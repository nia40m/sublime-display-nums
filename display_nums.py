import sublime
import sublime_plugin

import re
import json

plugin_settings = None

dec_re = re.compile(r"^(0|([1-9][0-9]*))(u|l|ul|lu|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]+)(u|l|ul|lu|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ull|llu)?$", re.I)

space = "&nbsp;"
temp_small_space = "*"
small_space = "<span>"+space+"</span>"

def plugin_loaded():
    global plugin_settings
    plugin_settings = Settings("display_nums.sublime-settings")

# event on settings "add on change"
class Settings:
    def __init__(self, name):
        self.settings = sublime.load_settings(name)

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return object.__getattribute__(self.settings, name)

    def set_view_settings(self, settings):
        self.view_settings = settings

    def bit_length(self):
        if self.view_settings.has("disnum.bytes_in_word"):
            bytes_in_word = self.view_settings.get("disnum.bytes_in_word")
        else:
            bytes_in_word = self.settings.get("bytes_in_word", 4)

        if not isinstance(bytes_in_word, int):
            return 4 * 8

        return bytes_in_word * 8

    def is_positions_reversed(self):
        if self.view_settings.has("disnum.bit_positions_reversed"):
            position_reversed = self.view_settings.get("disnum.bit_positions_reversed")
        else:
           position_reversed = self.settings.get("bit_positions_reversed", False)

        if not isinstance(position_reversed, bool):
            return False

        return position_reversed

def format_str(string, num, separator=" "):
    res = string[-num:]
    string = string[:-num]
    while len(string):
        res = string[-num:] + separator + res
        string = string[:-num]

    return res

def get_bits_positions(bits_in_word):
    positions = ""
    start = 0
    reversed_bits = plugin_settings.is_positions_reversed()

    while start < bits_in_word:
        if reversed_bits:
            positions += "{: <4}".format(start)
        else:
            positions = "{: >4}".format(start) + positions

        start += 4

    positions = format_str(positions, 2, temp_small_space*3)
    positions = positions.replace(" ", space).replace(temp_small_space, small_space)

    return positions

def prepare_urls(s, base, num):
    res = ""
    offset = 0
    for c in s[::-1]:
        if c.isdigit():
            res = """<a id='bits' href='{{
                    "num":{},
                    "base":{},
                    "offset":{}
                }}'>{}</a>""".format(num, base, offset, c) + res
            offset += 1
        else:
            res = c + res

    return res

def parse_number(text):
    match = dec_re.match(text)
    if match:
        return int(match.group(1), 10), 10

    match = hex_re.match(text)
    if match:
        return int(match.group(1), 16), 16

    match = oct_re.match(text)
    if match:
        return int(match.group(1), 8), 8

    match = bin_re.match(text)
    if match:
        return int(match.group(1), 2), 2

class DisplayNumberListener(sublime_plugin.EventListener):
    def on_selection_modified_async(self, view):
        # if more then one select close popup
        if len(view.sel()) > 1:
            return

        v = parse_number(view.substr(view.sel()[0]).strip())
        if v is None:
            return

        number, base = v

        # select max between (bit_length in settings) and (bit_length of selected number aligned to 4)
        bits_in_word = max(plugin_settings.bit_length(), number.bit_length() + ((-number.bit_length()) & 0x3))

        positions = get_bits_positions(bits_in_word)

        html = """
            <body id=show>
                <style>
                    span  {{ font-size: 0.35rem; }}
                    #swap {{ color: var(--yellowish); }}
                    #bits {{ color: var(--foreground); }}
                </style>
                <div><a href='{{"base":16, "num":{0}}}'>Hex</a>: {1}</div>
                <div><a href='{{"base":10, "num":{0}}}'>Dec</a>: {2}</div>
                <div><a href='{{"base":8, "num":{0}}}'>Oct</a>: {3}</div>
                <div><a href='{{"base":2, "num":{0}}}'>Bin</a>: {4}</div>
                <div><a id='swap' href='{{}}'>swap</a> {5}</div>
            </body>
        """.format(
            number,
            format_str("{:x}".format(number), 2),
            format_str("{}".format(number), 3, ","),
            format_str("{:o}".format(number), 3),
            prepare_urls(
                format_str(
                    format_str(
                        "{:0={}b}".format(number, bits_in_word),
                        4,
                        temp_small_space),
                    1,
                    temp_small_space),
                base,
                number
            ).replace(temp_small_space, small_space),
            positions
        )

        def select_function(x):
            data = json.loads(x)
            if data.get("offset") is not None:
                view.run_command("change_bit", data)
            elif data.get("num") is not None:
                view.run_command("convert_number", data)
            else:
                view.run_command("swap_positions")

        view.show_popup(
            html,
            max_width = 1024,
            location = view.sel()[0].a,
            on_navigate = select_function
        )

    def on_activated_async(self, view):
        plugin_settings.set_view_settings(view.settings())

def convert_number(num, base):
    if base == 10:
        return "{:d}".format(num)
    elif base == 16:
        return "0x{:x}".format(num)
    elif base == 2:
        return "0b{:b}".format(num)
    else:
        return "0{:o}".format(num)

class ConvertNumberCommand(sublime_plugin.TextCommand):
    def run(self, edit, base, num = None):
        selected_range = self.view.sel()[0]

        if num is not None:
            self.view.replace(edit, selected_range, convert_number(num, base))
            return

        selected_number = self.view.substr(selected_range).strip()

        v = parse_number(selected_number)
        if v is None:
            return

        num, _ = v

        self.view.replace(edit, selected_range, convert_number(num, base))

class ChangeBitCommand(sublime_plugin.TextCommand):
    def run(self, edit, num, base, offset):
        selected_range = self.view.sel()[0]
        self.view.replace(edit, selected_range, convert_number(num ^ (1 << offset), base))

class SwapPositionsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        plugin_settings.set("bit_positions_reversed", not plugin_settings.is_positions_reversed())

        selected_range = self.view.sel()[0]
        self.view.replace(edit, selected_range, self.view.substr(selected_range).strip())
