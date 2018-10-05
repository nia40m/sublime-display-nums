import sublime
import sublime_plugin

import re
import json

plugin_settings = sublime.load_settings("display_nums.sublime-settings")

dec_re = re.compile(r"^([1-9][0-9]*)(u|l|ul|lu|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]*)(u|l|ul|lu|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ull|llu)?$", re.I)

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

def get_bits(settings):
    bytes_in_word = settings.get("bytes_in_word", 4)

    if type(bytes_in_word) != int:
        bytes_in_word = 4

    return bytes_in_word*8

def align_to_octet(num):
    while num % 4:
        num += 1

    return num

class DisplayNumberListener(sublime_plugin.EventListener):
    def on_selection_modified_async(self, view):
        selected = view.substr(view.sel()[0]).strip()

        v = parse_number(selected)
        if v is None:
            return

        selected, base = v

        bits_in_word = get_bits(plugin_settings)
        if bits_in_word < selected.bit_length():
            bits_in_word = align_to_octet(selected.bit_length())

        positions = ""
        bit_nums = bits_in_word
        i = 0
        while i < bit_nums:
            positions = "{: =5}".format(i) + positions
            i += 4

        positions = (" "*4) + positions
        # rjust дополняет нужными символами до нужной длинны строки

        def prepare_urls(s, base, num):
            res = ""
            offset = 0
            for c in s[::-1]:
                if c != " ":
                    res = """<a href='{{"num":{},"base":{}, "offset":{}}}'>{}</a>""".format(num, base, offset, c) + res
                    offset += 1
                else:
                    res = c + res

            return res

        html = """
            <body id=show>
                <div><a href='{{"num":{0},"base":16}}'>Hex</a>: {1}</div>
                <div><a href='{{"num":{0},"base":10}}'>Dec</a>: {2}</div>
                <div><a href='{{"num":{0},"base":8}}'>Oct</a>: {3}</div>
                <div><a href='{{"num":{0},"base":2}}'>Bin</a>: {4}</div>
                <div>{5}</div>
            </body>
        """.format(
            selected,
            format_str("{:x}".format(selected), 2),
            format_str("{}".format(selected), 3, ","),
            format_str("{:o}".format(selected), 3),
            prepare_urls(format_str("{:0={}b}".format(selected, bits_in_word), 4), base, selected),
            positions.replace(" ", "&nbsp;")
        )

        def select_function(x):
            data = json.loads(x)
            if data.get("offset") is None:
                view.run_command("convert_number", data)
            else:
                view.run_command("change_bit", data)

        view.show_popup(html, max_width = 1024, on_navigate = select_function)

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
        selected = self.view.sel()[0]

        self.view.replace(edit, selected, convert_number(num, base))

class ChangeBitCommand(sublime_plugin.TextCommand):
    def run(self, edit, num, base, offset):
        selected = self.view.sel()[0]

        self.view.replace(edit, selected, convert_number(num ^ (1 << offset), base))