import sublime
import sublime_plugin

import struct
import re
import json

popup_mode_list = ["basic", "extended", "tabled"]

split_re = re.compile(r"\B_\B", re.I)
dec_re = re.compile(r"^(0|([1-9][0-9]*))(u|l|ul|lu|ll|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)

#####
# Sublime settings getters
#####
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

def get_swap_addition(project_settings):
    swap = get_setting_by_name(project_settings, "addition_swap_endianness")

    if not isinstance(swap, bool):
        return False

    return swap

def get_float_addition(project_settings):
    float_nums = get_setting_by_name(project_settings, "addition_float_from_hex")

    if not isinstance(float_nums, bool):
        return False

    return float_nums

#####
# Pop-up string generators
#####
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

html_basic = """
<body id='show'>
    <style>
        span  {{ font-size: 0.35rem; }}
        #swap {{ color: var(--yellowish); }}
        #bits {{ color: var(--foreground); }}
        #hr   {{ margin: 5px 0; }}
    </style>
    <div>{hex_name}:&nbsp;{hex_num}</div>
    <div>{dec_name}:&nbsp;{dec_num}</div>
    <div>{oct_name}:&nbsp;{oct_num}</div>
    <div>{bin_name}:&nbsp;{bin_num}</div>
    <div id='swap'>""" + "&nbsp;"*5 + """{pos}</div>
    {additional}
</body>
"""

html_hr = "<div id='hr'></div>"

str_convert_number = """<a href='{{ "func": "convert_number","data": {{ "base":{base} }}}}'>{name}</a>"""

feature_swap_endian = """
<div id='options'>Swap endianness as
    <a href='{ "func": "swap_endianness", "data" : { "bits": 16 } }'>16 bit</a>
    <a href='{ "func": "swap_endianness", "data" : { "bits": 32 } }'>32 bit</a>
    <a href='{ "func": "swap_endianness", "data" : { "bits": 64 } }'>64 bit</a>
</div>
"""

def feature_float_numbers(number, bits_count):
    res = ""

    if bits_count/8 <= 4:
        res += "<div>Float:&nbsp;&nbsp;{}</div>".format(struct.unpack('!f',struct.pack('!I',number))[0])

    if bits_count/8 <= 8:
        res += "<div>Double:&nbsp;{}</div>".format(struct.unpack('!d',struct.pack('!Q',number))[0])

    return res

def create_popup_content(settings, mode, number, base):
    # select max between (bit_length in settings) and (bit_length of selected number aligned to 4)
    curr_bits_in_word = max(get_bits_in_word(settings), number.bit_length() + ((-number.bit_length()) & 0x3))

    hex_num = format_str("{:x}".format(number), 2)
    dec_num = format_str("{}".format(number), 3, ",")
    oct_num = format_str("{:o}".format(number), 3)
    bin_num = prepare_urls(
                format_str(
                    format_str(
                        "{:0={}b}".format(number, curr_bits_in_word),
                        4,
                        temp_small_space),
                    1,
                    temp_small_space),
                base,
                number
            ).replace(temp_small_space, small_space)

    hex_name = "Hex"
    dec_name = "Dec"
    oct_name = "Oct"
    bin_name = "Bin"
    additional = ""

    if mode == "extended":
        hex_name = str_convert_number.format(name=hex_name,base=16)
        dec_name = str_convert_number.format(name=dec_name,base=10)
        oct_name = str_convert_number.format(name=oct_name,base=8)
        bin_name = str_convert_number.format(name=bin_name,base=2)

        if get_swap_addition(settings):
            additional += html_hr
            additional += feature_swap_endian

        if base == 16 and get_float_addition(settings):
            additional += html_hr
            additional += feature_float_numbers(number, curr_bits_in_word)


    return html_basic.format(
            hex_name = hex_name,
            dec_name = dec_name,
            oct_name = oct_name,
            bin_name = bin_name,
            hex_num = hex_num,
            dec_num = dec_num,
            oct_num = oct_num,
            bin_num = bin_num,
            pos = get_bits_positions(settings, curr_bits_in_word),
            additional = additional
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

#####
# Main listener of selection event
#####
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

#####
# Sublime commands
#####
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
