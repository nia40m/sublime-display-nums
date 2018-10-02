import sublime
import sublime_plugin

import re
import json

dec_re = re.compile(r"^([1-9][0-9]*)(u|l|ul|lu|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]*)(u|l|ul|lu|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ull|llu)?$", re.I)

def format_str(string, num, separator=" "):
    res = string[-num:]
    string = string[:-num]
    while (len(string)):
        res = string[-num:] + separator + res
        string = string[:-num]

    return res

def parse_number(text):
    match = dec_re.match(text)
    if match:
        return int(match.group(1), 10)

    match = hex_re.match(text)
    if match:
        return int(match.group(1), 16)

    match = oct_re.match(text)
    if match:
        return int(match.group(1), 8)

    match = bin_re.match(text)
    if match:
        return int(match.group(1), 2)

class DisplayNumberListener(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        selected = view.substr(view.sel()[0]).strip()

        selected = parse_number(selected)
        if selected is None:
            return

        html = """
            <style>
                span {{
                    font-size: 6px;
                }}
            </style>
            <body id=show>
                <div><a href='{{\"num\":{0},\"base\":16}}'>Hex</a>: {1}</div>
                <div><a href='{{\"num\":{0},\"base\":10}}'>Dec</a>: {2}</div>
                <div><a href='{{\"num\":{0},\"base\":8}}'>Oct</a>: {3}</div>
                <div><a href='{{\"num\":{0},\"base\":2}}'>Bin</a>: {4}</div>
            </body>
        """.format(
            selected,
            format_str("{:x}".format(selected), 2),
            format_str("{}".format(selected), 3, ","),
            format_str("{:o}".format(selected), 3),
            format_str("{:b}".format(selected), 4)
        )

        view.show_popup(html, max_width = 1024, on_navigate = lambda x: view.run_command("convert_number", json.loads(x)))

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
