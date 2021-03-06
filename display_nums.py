import sublime
import sublime_plugin

import re
import json

popup_mode_list = ["basic", "extended", "tabled"]

split_re = re.compile(r"\B_\B", re.I)
dec_re = re.compile(r"^(0|([1-9][0-9]*))(u|l|ul|lu|ll|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)

space = "&nbsp;"
temp_small_space = "*"
small_space = "<span>"+space+"</span>"

def get_setting_by_name(project_settings, name):
    if project_settings.has("disnum." + name):
        return project_settings.get("disnum." + name)
    else:
        return sublime.load_settings("display_nums.sublime-settings").get(name)

def get_bits_in_word(project_settings):
    bytes_in_word = get_setting_by_name(project_settings, "bytes_in_word")

    if not isinstance(bytes_in_word, int):
        return 4 * 8

    return bytes_in_word * 8

def get_positions_reversed(project_settings):
    position_reversed = get_setting_by_name(project_settings, "bit_positions_reversed")

    if not isinstance(position_reversed, bool):
        return False

    return position_reversed

def reverse_positions_reversed(project_settings):
    if project_settings.has("disnum.bit_positions_reversed"):
        project_settings.set("disnum.bit_positions_reversed", not get_positions_reversed(project_settings))
    else:
        sublime.load_settings("display_nums.sublime-settings").set("bit_positions_reversed", not get_positions_reversed(project_settings))

def get_popup_mode(project_settings):
    extended = get_setting_by_name(project_settings, "plugin_mode")

    if not isinstance(extended, str):
        return "basic"

    return extended

def get_mouse_move_option(project_settings):
    mouse_move = get_setting_by_name(project_settings, "hide_on_mouse_move_away")

    if not isinstance(mouse_move, bool):
        return sublime.HIDE_ON_MOUSE_MOVE_AWAY

    return sublime.HIDE_ON_MOUSE_MOVE_AWAY if mouse_move else 0

def format_str(string, num, separator=" "):
    res = string[-num:]
    string = string[:-num]
    while len(string):
        res = string[-num:] + separator + res
        string = string[:-num]

    return res

def get_bits_positions(settings, curr_bits_in_word):
    positions = ""
    start = 0

    while start < curr_bits_in_word:
        if get_positions_reversed(settings):
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
    # remove underscores in the number
    text = "".join(split_re.split(text))

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
    <div>Hex:&nbsp;{hex}</div>
    <div>Dec:&nbsp;{dec}</div>
    <div>Oct:&nbsp;{oct}</div>
    <div>Bin:&nbsp;{bin}</div>
    <div id='swap'><a id='swap' href='{{ "func": "swap_positions",
        "data": {{ "base":{base}, "num":{num} }}
    }}'>swap</a>&nbsp;{pos}</div>
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
    }}'>Hex</a>:&nbsp;{hex}</div>
    <div><a href='{{ "func": "convert_number",
        "data": {{ "base":10 }}
    }}'>Dec</a>:&nbsp;{dec}</div>
    <div><a href='{{ "func": "convert_number",
        "data": {{ "base":8 }}
    }}'>Oct</a>:&nbsp;{oct}</div>
    <div><a href='{{ "func": "convert_number",
        "data": {{ "base":2 }}
    }}'>Bin</a>:&nbsp;{bin}</div>
    <div id='swap'><a id='swap' href='{{ "func": "swap_positions",
        "data": {{ "base":{base}, "num":{num} }}
    }}'>swap</a>&nbsp;{pos}</div>
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

def create_popup_content(settings, mode, number, base):
    # select max between (bit_length in settings) and (bit_length of selected number aligned to 4)
    curr_bits_in_word = max(get_bits_in_word(settings), number.bit_length() + ((-number.bit_length()) & 0x3))

    if mode == "extended":
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
            pos = get_bits_positions(settings, curr_bits_in_word)
        )

def create_tabled_popup_content(number, hex_num):
    name = ["Hex", "Dec", "Bin"]
    base = [16, 10, 2]

    # calculate length of strings
    lens = [
        max(len(name[0]), len(number)),
        len('{:x}'.format(hex_num)),
        max(len(name[0]), len('{:d}'.format(hex_num))),
        len('{:b}'.format(hex_num))
    ]

    html = "<u>{}  {}  {}  {}</u>".format(
        "{: <{}}".format(number, lens[0]),
        "{: <{}}".format(name[0], lens[1] + len("0x")),
        "{: <{}}".format(name[1], lens[2]),
        "{: <{}}".format(name[2], lens[3] + len("0b"))
    )

    # convert from every numeral system
    for i in range(0, len(name)):
        try:
            num = int(number, base[i])
        except:
            continue

        html += "<div>{}  0x{}  {}  0b{}</div>".format(
            "{: <{}}".format(name[i], lens[0]),
            "{: <{}X}".format(num, lens[1]),
            "{: <{}d}".format(num, lens[2]),
            "{: <{}b}".format(num, lens[3])
        )

    return html.replace(" ", space)

class DisplayNumberListener(sublime_plugin.EventListener):
    def on_selection_modified_async(self, view):
        # if more then one select close popup
        if len(view.sel()) > 1:
            return view.hide_popup()

        # selected string without spaces
        string = view.substr(view.sel()[0]).strip()

        # get plugin mode
        mode = get_popup_mode(view.settings())
        if mode not in popup_mode_list:
            return

        if mode == "tabled":
            # trying to convert string as hex
            try:
                hex_num = int(string, 16)
            except:
                return

            html = create_tabled_popup_content(string, hex_num)
        else:
            parsed = parse_number(string)
            if parsed is None:
                return

            html = create_popup_content(view.settings(), mode, parsed["number"], parsed["base"])

        def select_function(x):
            data = json.loads(x)

            if data.get("func") is not None:
                view.run_command(data.get("func"), data.get("data"))

        view.show_popup(
            html,
            flags=get_mouse_move_option(view.settings()),
            max_width = 1024,
            location = view.sel()[0].begin(),
            on_navigate = select_function
        )

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
        reverse_positions_reversed(self.view.settings())

        self.view.update_popup(create_popup_content(self.view.settings(), num, base))

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
