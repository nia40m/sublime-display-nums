import sublime
import sublime_plugin

import re
import json

plugin_settings = None
bits_in_word = None
position_reversed = None

dec_re = re.compile(r"^(0|([1-9][0-9]*))(u|l|ul|lu|ll|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)

space = "&nbsp;"
temp_small_space = "*"
small_space = "<span>"+space+"</span>"

def plugin_loaded():
    global plugin_settings
    plugin_settings = sublime.load_settings("display_nums.sublime-settings")

    plugin_settings.add_on_change("bytes_in_word", get_bits_in_word)
    plugin_settings.add_on_change("bit_positions_reversed", get_positions_reversed)

def get_bits_in_word():
    global plugin_settings
    global bits_in_word
    project_settings = sublime.active_window().active_view().settings()

    if project_settings.has("disnum.bytes_in_word"):
        bytes_in_word = project_settings.get("disnum.bytes_in_word")
    else:
        bytes_in_word = plugin_settings.get("bytes_in_word")

    if not isinstance(bytes_in_word, int):
        bits_in_word = 4 * 8

    bits_in_word = bytes_in_word * 8

def get_positions_reversed():
    global plugin_settings
    global position_reversed
    project_settings = sublime.active_window().active_view().settings()

    if project_settings.has("disnum.bit_positions_reversed"):
        position_reversed = project_settings.get("disnum.bit_positions_reversed")
    else:
        position_reversed = plugin_settings.get("bit_positions_reversed")

    if not isinstance(position_reversed, bool):
        position_reversed = False

def get_popup_mode():
    global plugin_settings
    project_settings = sublime.active_window().active_view().settings()

    if project_settings.has("disnum.extended_mode"):
        return project_settings.get("disnum.extended_mode")

    extended = plugin_settings.get("extended_mode")

    if not isinstance(extended, bool):
        return False

    return extended

def format_str(string, num, separator=" "):
    res = string[-num:]
    string = string[:-num]
    while len(string):
        res = string[-num:] + separator + res
        string = string[:-num]

    return res

def get_bits_positions(curr_bits_in_word):
    global position_reversed
    positions = ""
    start = 0

    while start < curr_bits_in_word:
        if position_reversed:
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

    bit = """<a id='bits' href='{{ "func":"{func}",
        "data":{{ "num":{num}, "base":{base}, "offset":{offset} }}
        }}'>{char}</a>"""

    for c in s[::-1]:
        if c.isdigit():
            res = bit.format(
                func = "change_bit", num = num, base = base, offset = offset, char = c
                ) + res

            offset += 1
        else:
            res = c + res

    return res

def parse_number(text):
    match = dec_re.match(text)
    if match:
        return {"number": int(match.group(1), 10), "base": 10}

    match = hex_re.match(text)
    if match:
        return {"number": int(match.group(1), 16), "base": 16}

    match = oct_re.match(text)
    if match:
        return {"number": int(match.group(1), 8), "base": 8}

    match = bin_re.match(text)
    if match:
        return {"number": int(match.group(1), 2), "base": 2}

html_basic = """
<body id='show'>
    <style>
        span  {{ font-size: 0.35rem; }}
        #swap {{ color: var(--yellowish); }}
        #bits {{ color: var(--foreground); }}
    </style>
    <div>Hex: {hex}</div>
    <div>Dec: {dec}</div>
    <div>Oct: {oct}</div>
    <div>Bin: {bin}</div>
    <div id='swap'><a id='swap' href='{{ "func": "swap_positions",
        "data": {{ "base":{base}, "num":{num} }}
    }}'>swap</a> {pos}</div>
</body>
"""

html_extended = """
<body id='show'>
    <style>
        span  {{ font-size: 0.35rem; }}
        #swap {{ color: var(--yellowish); }}
        #bits {{ color: var(--foreground); }}
        #options {{ margin-top: 10px; }}
    </style>
    <div><a href='{{ "func": "convert_number",
        "data": {{ "base":16 }}
    }}'>Hex</a>: {hex}</div>
    <div><a href='{{ "func": "convert_number",
        "data": {{ "base":10 }}
    }}'>Dec</a>: {dec}</div>
    <div><a href='{{ "func": "convert_number",
        "data": {{ "base":8 }}
    }}'>Oct</a>: {oct}</div>
    <div><a href='{{ "func": "convert_number",
        "data": {{ "base":2 }}
    }}'>Bin</a>: {bin}</div>
    <div id='swap'><a id='swap' href='{{ "func": "swap_positions",
        "data": {{ "base":{base}, "num":{num} }}
    }}'>swap</a> {pos}</div>
    <div id='options'>Swap endianness as
        <a href='{{ "func": "swap_endianness", "data" : {{ "bits": 16 }} }}'>
        16 bit</a>
        <a href='{{ "func": "swap_endianness", "data" : {{ "bits": 32 }} }}'>
        32 bit</a>
        <a href='{{ "func": "swap_endianness", "data" : {{ "bits": 64 }} }}'>
        64 bit</a>
    </div>
</body>
"""

def create_popup_content(number, base):
    global bits_in_word

    # select max between (bit_length in settings) and (bit_length of selected number aligned to 4)
    curr_bits_in_word = max(bits_in_word, number.bit_length() + ((-number.bit_length()) & 0x3))

    if get_popup_mode():
        html = html_extended
    else:
        html = html_basic

    return html.format(
            num = number,
            base = base,
            hex = format_str("{:x}".format(number), 2),
            dec = format_str("{}".format(number), 3, ","),
            oct = format_str("{:o}".format(number), 3),
            bin = prepare_urls(
                format_str(
                    format_str(
                        "{:0={}b}".format(number, curr_bits_in_word),
                        4,
                        temp_small_space),
                    1,
                    temp_small_space),
                base,
                number
            ).replace(temp_small_space, small_space),
            pos = get_bits_positions(curr_bits_in_word)
        )

class DisplayNumberListener(sublime_plugin.EventListener):
    def on_selection_modified_async(self, view):
        # if more then one select close popup
        if len(view.sel()) > 1:
            return view.hide_popup()

        parsed = parse_number(view.substr(view.sel()[0]).strip())
        if parsed is None:
            return

        def select_function(x):
            data = json.loads(x)

            if data.get("func") is not None:
                view.run_command(data.get("func"), data.get("data"))

        view.show_popup(
            create_popup_content(parsed["number"], parsed["base"]),
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            max_width = 1024,
            location = view.sel()[0].begin(),
            on_navigate = select_function
        )

    def on_activated_async(self, view):
        view.settings().clear_on_change("disnum.bytes_in_word")
        view.settings().add_on_change("disnum.bytes_in_word", get_bits_in_word)

        view.settings().clear_on_change("disnum.bit_positions_reversed")
        view.settings().add_on_change("disnum.bit_positions_reversed", get_positions_reversed)

        get_bits_in_word()
        get_positions_reversed()

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
    def run(self, edit, base):
        if len(self.view.sel()) > 1:
            return self.view.hide_popup()

        selected_range = self.view.sel()[0]
        selected_number = self.view.substr(selected_range).strip()

        parsed = parse_number(selected_number)
        if parsed is None:
            return self.view.hide_popup()

        self.view.replace(edit, selected_range, convert_number(parsed["number"], base))

class ChangeBitCommand(sublime_plugin.TextCommand):
    def run(self, edit, base, num, offset):
        selected_range = self.view.sel()[0]
        self.view.replace(edit, selected_range, convert_number(num ^ (1 << offset), base))

class SwapPositionsCommand(sublime_plugin.TextCommand):
    def run(self, edit, base, num):
        global position_reversed
        position_reversed = not position_reversed

        self.view.update_popup(create_popup_content(num, base))

class SwapEndiannessCommand(sublime_plugin.TextCommand):
    def run(self, edit, bits):
        if len(self.view.sel()) > 1:
            return self.view.hide_popup()

        selected_range = self.view.sel()[0]
        selected_number = self.view.substr(selected_range).strip()

        parsed = parse_number(selected_number)
        if parsed is None:
            return self.view.hide_popup()

        bit_len = parsed["number"].bit_length()
        # align bit length to bits
        bit_len = bit_len + ((-bit_len) & (bits - 1))

        bytes_len = bit_len // 8

        number = parsed["number"].to_bytes(bytes_len, byteorder="big")

        bytes_word = bits // 8

        result = []

        for i in range(bytes_word, bytes_len + 1, bytes_word):
            for j in range(0, bytes_word):
                result.append(number[i - j - 1])

        result = int.from_bytes(bytes(result), byteorder="big")

        self.view.replace(edit, selected_range, convert_number(result, parsed["base"]))
