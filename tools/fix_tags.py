# -*- coding: utf-8 -*-
"""Make translated .ks survive TyranoScript's tag parser.

kag.parser.js makeTag() deletes every ' ' inside a quoted attribute value
(fine for Chinese/Japanese, fatal for Korean word spacing) and turns an empty
"" into the string "undefined".  So, inside [tags] only:

  - `attr=""text""`  (translator swapped the Chinese “ ” for ASCII quotes)
    -> `attr="“text”"`
  - spaces in a value that contains Hangul -> U+2005 FOUR-PER-EM SPACE
    (survives the parser, still a line-break opportunity in the browser)

Plus layout tweaks that only make sense for Korean.
"""
import re

SPACE = "\u2005"
TAG = re.compile(r"\[[^\[\]]*\]")
BROKEN = re.compile(r'(\w+)=""([^"]+?)""')
ATTR = re.compile(r'(\w+)(\s*=\s*)"([^"]*)"')
HANGUL = re.compile("[\uac00-\ud7a3]")

# title menu: 4 Korean labels at size 40 overflow the 320px column -> 2 lines
LAYOUT = {
    "title_screen.ks": [('font_color="white"  text=', 'font_color="white"  size="32"  text='),
                        ('  size="40"  target=', '  target=')],
}


def _fix_tag(tag):
    tag = BROKEN.sub(lambda m: f'{m.group(1)}="“{m.group(2)}”"', tag)

    def attr(m):
        v = m.group(3)
        if HANGUL.search(v):
            v = v.replace(" ", SPACE)
        return f'{m.group(1)}{m.group(2)}"{v}"'
    return ATTR.sub(attr, tag)


def fix_ks(name, text):
    out = []
    for line in text.split("\n"):
        out.append(TAG.sub(lambda m: _fix_tag(m.group(0)), line))
    text = "\n".join(out)
    for a, b in LAYOUT.get(name, []):
        text = text.replace(a, b)
    return text
