import sublime
import sublime_plugin

import re
import json

plugin_settings = sublime.load_settings("display_nums.sublime-settings")

dec_re = re.compile(r"^(0|([1-9][0-9]*))(u|l|ul|lu|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]+)(u|l|ul|lu|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ull|llu)?$", re.I)

space = "&nbsp;"
temp_small_space = "*"
small_space = "<span>"+space+"</span>"

def format_str(string, num, separator=" "):
    res = string[-num:]
    string = string[:-num]
    while len(string):
        res = string[-num:] + separator + res
        string = string[:-num]

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

def get_bits(settings, number_bit_len):
    bytes_in_word = settings.get("bytes_in_word", 4)

    if type(bytes_in_word) != int:
        bytes_in_word = 4

    bytes_in_word *= 8

    if bytes_in_word < number_bit_len:
        return number_bit_len

    return bytes_in_word

def is_positions_reversed(settings):
    position_reversed = settings.get("bit_positions_reversed", False)

    if type(position_reversed) != bool:
        position_reversed = False

    return position_reversed

def align_to_octet(num):
    while num % 4:
        num += 1

    return num

def get_bits_positions(bits_in_word):
    positions = ""
    start = 0
    reversed_bits = is_positions_reversed(plugin_settings)

    while start < bits_in_word:
        if reversed_bits:
            positions += "{: <4}".format(start)
        else:
            positions = "{: >4}".format(start) + positions

        start += 4

    positions = format_str(positions, 2, temp_small_space*3)
    positions = positions.replace(" ", space).replace(temp_small_space, small_space)

    return positions

class DisplayNumberListener(sublime_plugin.EventListener):
    def on_selection_modified_async(self, view):
        selected_number = view.substr(view.sel()[0]).strip()

        v = parse_number(selected_number)
        if v is None:
            return

        selected_number, base = v

        bits_in_word = get_bits(plugin_settings, align_to_octet(selected_number.bit_length()))

        positions = get_bits_positions(bits_in_word)

        def prepare_urls(s, base, num):
            res = ""
            offset = 0
            for c in s[::-1]:
                if c.isdigit():
                    res = """<a href='{{"num":{},"base":{}, "offset":{}}}'>{}</a>""".format(num, base, offset, c) + res
                    offset += 1
                else:
                    res = c + res

            return res

        html = """
            <body id=show>
                <style>
                    span {{ font-size: 0.35rem; }}
                </style>
                <div><a href='{{"num":{0},"base":16}}'>Hex</a>: {1}</div>
                <div><a href='{{"num":{0},"base":10}}'>Dec</a>: {2}</div>
                <div><a href='{{"num":{0},"base":8}}'>Oct</a>: {3}</div>
                <div><a href='{{"num":{0},"base":2}}'>Bin</a>: {4}</div>
                <div><a href='{{}}'>swap</a> {5}</div>
            </body>
        """.format(
            selected_number,
            format_str("{:x}".format(selected_number), 2),
            format_str("{}".format(selected_number), 3, ","),
            format_str("{:o}".format(selected_number), 3),
            prepare_urls(
                format_str(format_str("{:0={}b}".format(selected_number, bits_in_word), 4, temp_small_space), 1, temp_small_space),
                base,
                selected_number
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

        view.show_popup(html, max_width = 1024, location = view.sel()[0].a, on_navigate = select_function)

def convert_number(num, base):
    if base == 10:
        return str(num)
    elif base == 16:
        return hex(num)
    elif base == 2:
        return bin(num)
    else:
        return oct(num).replace("o", "")

class ConvertNumberCommand(sublime_plugin.TextCommand):
    def run(self, edit, num = 0, base = 10):
        selected_range = self.view.sel()[0]

        self.view.replace(edit, selected_range, convert_number(num, base))

class ChangeBitCommand(sublime_plugin.TextCommand):
    def run(self, edit, num, base, offset):
        selected_range = self.view.sel()[0]

        self.view.replace(edit, selected_range, convert_number(num ^ (1 << offset), base))

class SwapPositionsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        plugin_settings.set("bit_positions_reversed", not is_positions_reversed(plugin_settings))

        selected_range = self.view.sel()[0]
        self.view.replace(edit, selected_range, self.view.substr(selected_range).strip())
