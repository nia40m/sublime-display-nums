import sublime
import sublime_plugin

import re

def format_str(string, num, separator=" "):
    res = string[-num:]
    string = string[:-num]
    while (len(string)):
        res = string[-num:] + separator + res
        string = string[:-num]

    return res

def is_num(s):
    return re.match(r"^[1-9][0-9]*(u|l|ul|lu|ull|llu)?$", s or "", re.I) is not None

def is_hex(s):
    return re.match(r"^0x[0-9a-f]+(u|l|ul|lu|ull|llu)?$", s or "", re.I) is not None

def is_oct(s):
    return re.match(r"^0[0-7]*(u|l|ul|lu|ull|llu)?$", s or "", re.I) is not None

class DisplayNumberCommand(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        selected = view.substr(view.sel()[0]).strip()

        if is_num(selected):
            selected = int(selected.rstrip("uUlL"), 10)
        elif is_hex(selected):
            selected = int(selected.rstrip("uUlL"), 16)
        elif is_oct(selected):
            selected = int(selected.rstrip("uUlL"), 8)
        else:
            return False

        html = """
            <body id=show>
                <div>Dec: %s</div>
                <div>Hex: %s</div>
                <div>Bin: %s</div>
                <div>Oct: %s</div>
            </body>
        """ % (
            format_str(str(selected), 3, ","),
            format_str(hex(selected)[2:], 2),
            format_str(bin(selected)[2:], 4),
            format_str(oct(selected)[2:], 3)
        )

        view.show_popup(html, max_width=512)
