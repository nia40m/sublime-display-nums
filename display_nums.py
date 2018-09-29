import sublime
import sublime_plugin

import re

def format_str(string, num):
    res = ""
    while (len(string)):
        res = string[-num:] + " " + res
        string = string[:-num]

    return res

def is_num(s):
    return re.match(r"^[+-]?[0-9]+$", s or "") is not None

def is_hex(s):
    return re.match(r"^0x[0-9a-fA-F]+$", s or "") is not None

class DisplayNumberCommand(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        selected = view.substr(view.sel()[0]).strip()

        if is_num(selected):
            selected = int(selected, 10)
        elif is_hex(selected):
            selected = int(selected, 16)
        else:
            return False

        html = """
            <body id=show>
                <style>
                    p {
                        margin-top: 0;
                    }
                </style>
                <div>Int: %s</div>
                <div>Hex: %s</div>
                <div>Bin: %s</div>
                <div>Oct: %s</div>
            </body>
        """ % (
            format_str(str(selected), 3),
            format_str(hex(selected)[2:], 2),
            format_str(bin(selected)[2:], 4),
            format_str(oct(selected)[2:], 3)
        )

        view.show_popup(html, max_width=512, on_navigate=lambda x: copy(self.view, x))
