import sublime
import sublime_plugin

import re

dec_re = re.compile(r"^([1-9][0-9]*)(u|l|ul|lu|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]*)(u|l|ul|lu|ull|llu)?$", re.I)

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

class DisplayNumberCommand(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        selected = view.substr(view.sel()[0]).strip()

        selected = parse_number(selected)
        if selected is None:
            return

        html = """
            <body id=show>
                <div>Dec: %s</div>
                <div>Hex: %s</div>
                <div>Bin: %s</div>
                <div>Oct: %s</div>
            </body>
        """ % (
            format_str("{}".format(selected), 3, ","),
            format_str("{:x}".format(selected), 2),
            format_str("{:b}".format(selected), 4),
            format_str("{:o}".format(selected), 3)
        )

        view.show_popup(html, max_width=512)
