#!/usr/bin/env python3
"""Generates the Vitesse Islands theme plugin (Dark + Soft) for JetBrains IDEs.

usage: build.py <Islands Dark theme.json> <RiderIslandsDark.xml> <out dir>

Inputs are upstream files (see build.sh for pinned versions):
  * Islands Dark UI theme      - JetBrains/intellij-community (Apache-2.0)
  * Rider Islands Dark scheme  - JetBrains/rider-theme-pack   (Apache-2.0)
Palette and token mapping are based on Vitesse by Anthony Fu (MIT).
Both inputs are modified: colours are remapped to the Vitesse palette and
editor attributes are overridden (see NOTICE).
"""
import colorsys
import copy
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ISLANDS_THEME = Path(sys.argv[1])
RIDER_SCHEME = Path(sys.argv[2])
OUT = Path(sys.argv[3])


# ================================================================ colour utils
def h2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2h(c):
    return "".join(f"{max(0, min(255, round(x))):02X}" for x in c)


def blend(hexa, bg):
    """Flatten RRGGBBAA onto a background (editor schemes ignore alpha)."""
    h = hexa.lstrip("#")
    a = int(h[6:8], 16) / 255
    c, b = h2rgb(h[:6]), h2rgb(bg)
    return rgb2h(tuple(a * c[i] + (1 - a) * b[i] for i in range(3)))


def mix(a, b, t):
    ca, cb = h2rgb(a), h2rgb(b)
    return rgb2h(tuple(ca[i] + (cb[i] - ca[i]) * t for i in range(3)))


def to_hls(h):
    r, g, b = (x / 255 for x in h2rgb(h))
    return colorsys.rgb_to_hls(r, g, b)


def from_hls(hh, l, s):
    return rgb2h(tuple(x * 255 for x in colorsys.hls_to_rgb(hh, l, s)))


def boost(h, sat=1.38, light=0.06):
    """Soft variant: livelier syntax colours (more chroma, a touch lighter)."""
    hh, l, s = to_hls(h)
    return from_hls(hh, min(l + light, 0.86), min(s * sat, 0.75))


def lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(h2rgb(a)), lum(h2rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ================================================================ palette
# Syntax hues, tuned from Vitesse so neighbouring token kinds don't merge:
#   rose     keywords (bold) / operators      green   control flow (bold)
#   olive    methods (italic)                 cyan    classes, records (italic)
#   teal     structs, enums (italic)          blue    interfaces, delegates, type params
#   violet   namespaces                       pink    constants, enum members
#   sand     locals, fields                   gold    properties (italic)
#   clay     strings                          sea     numbers
SYNTAX = {
    "keyword": "CB7676",
    "control": "4D9375",
    "operator": "CB7676",
    "function": "80A665",
    "class": "5EAAB5",
    "struct": "5DA994",
    "interface": "6394BF",
    "namespace": "8A93C9",
    "constant": "C48FC8",
    "variable": "BD976A",
    "property": "CFBA6E",
    "string": "C98A7D",
    "number": "4C9A91",
    "escape": "D4976C",
    "event": "D4976C",
    "attribute": "D4976C",
    "decorator": "BD8F8F",
    "regex": "C4704F",
    "punctuation": "666666",
    # ansi / misc
    "green": "4D9375", "cyan": "5EAAB5", "blue": "6394BF", "red": "CB7676",
    "orange": "D4976C", "yellow": "E6CC77", "magenta": "D9739F",
}

VARIANTS = {
    "dark": {
        "name": "Vitesse Dark Islands",
        "id": "vitesse-dark-islands",
        "file": "VitesseDarkIslands",
        "bg": "121212", "bg_active": "181818",
        "fg_alpha": "dbd7caee",
        "gray": {
            10: "121212", 20: "181818", 30: "262626", 40: "2E2E2E", 50: "3A3A3A",
            60: "4A4A49", 70: "5C5B58", 80: "72706B", 90: "87857E", 100: "9C9990",
            110: "AFABA1", 120: "BFBBAF", 130: "CECABE", 140: "DCD9CE",
            150: "E8E6DD", 160: "F4F2EC",
        },
        "boost": False,
    },
    "soft": {
        "name": "Vitesse Soft Islands",
        "id": "vitesse-soft-islands",
        "file": "VitesseSoftIslands",
        "bg": "222222", "bg_active": "292929",
        "fg_alpha": "dbd7caff",
        "gray": {
            10: "222222", 20: "292929", 30: "333333", 40: "3B3B3B", 50: "464646",
            60: "545453", 70: "656461", 80: "797772", 90: "8D8B84", 100: "A19E95",
            110: "B3AFA5", 120: "C3BFB3", 130: "DBD7CA", 140: "E2DFD5",
            150: "EBE9E1", 160: "F6F4EE",
        },
        "boost": True,
    },
}

PRIMARY = "4D9375"
ISL_BLUE80_L = to_hls("3871E1")[1]


def make_palette(var):
    bg = var["bg"]
    S = {k: (boost(v) if var["boost"] else v) for k, v in SYNTAX.items()}
    if var["boost"]:
        S["punctuation"] = "7A7A7A"
    S.update({
        "bg": bg,
        "bg_active": var["bg_active"],
        "fg": blend(var["fg_alpha"], bg),
        "fg_active": "BFBAAA",
        "fg_secondary": blend("dedcd590", bg),
        "ignored": blend("dedcd550", bg),
        "comment": blend("758575dd", bg) if not var["boost"] else blend("8a9a8aee", bg),
        "primary": boost(PRIMARY, 1.15, 0.03) if var["boost"] else PRIMARY,
    })
    # surfaces derived from the background
    S["raised"] = mix(bg, "FFFFFF", 0.045)      # folded text, hints
    S["raised2"] = mix(bg, "FFFFFF", 0.085)
    S["green_tint"] = blend(S["primary"] + "30", bg)
    S["green_tint2"] = blend(S["primary"] + "48", bg)
    return S


# ================================================================ UI theme
def greenify(hexcol, primary):
    p_h, p_l, p_s = to_hls(primary)
    _, l, s = to_hls(hexcol)
    if l <= ISL_BLUE80_L:
        nl = l * p_l / ISL_BLUE80_L
    else:
        nl = p_l + (l - ISL_BLUE80_L) * (1 - p_l) / (1 - ISL_BLUE80_L)
    return from_hls(p_h, nl, min(min(s, 1.0) * (p_s / 0.73), 0.45))


def neutralize(hexcol, gray):
    rgb = {k: h2rgb(v) for k, v in gray.items()}
    L = lum(h2rgb(hexcol))
    steps = sorted(rgb.items(), key=lambda kv: lum(kv[1]))
    lo = steps[0]
    for st in steps:
        if lum(st[1]) <= L:
            lo = st
    hi = next((st for st in steps if lum(st[1]) >= L), steps[-1])
    l0, l1 = lum(lo[1]), lum(hi[1])
    t = 0 if l1 == l0 else (L - l0) / (l1 - l0)
    return rgb2h(tuple(lo[1][i] + (hi[1][i] - lo[1][i]) * t for i in range(3)))


def classify(hexcol):
    hh, l, s = to_hls(hexcol)
    deg = hh * 360
    coolish = 180 <= deg <= 260
    if s < 0.06 or (coolish and (s < 0.16 or (s < 0.25 and (l < 0.2 or l > 0.8)))):
        return "gray"
    if 200 <= deg <= 235 and s >= 0.25:
        return "blue"
    return "other"


def build_ui_theme(var, S):
    src = json.loads(ISLANDS_THEME.read_text())
    gray = var["gray"]
    colors = src["colors"]
    primary = S["primary"]

    def remap_hex(token):
        h = token.lstrip("#")
        rgb, alpha = h[:6], h[6:]
        if rgb.upper() in ("FFFFFF", "000000", "808080"):
            return token
        kind = classify(rgb)
        if kind == "gray":
            return "#" + neutralize(rgb, gray) + alpha
        if kind == "blue":
            return "#" + greenify(rgb, primary) + alpha
        return token

    for k in list(colors):
        m = re.fullmatch(r"gray-(\d+)", k)
        if m:
            colors[k] = "#" + gray[int(m.group(1))]
        m = re.fullmatch(r"blue-(\d+)", k)
        if m:
            colors[k] = "#" + greenify(colors[k], primary)

    bg = var["bg"]
    sel = blend(primary + "38", bg)
    sel_muted = blend(primary + "26", bg)
    colors.update({
        "blue-80": "#" + primary,
        "red-100": "#" + S["red"],
        "yellow-100": "#" + S["orange"],
        "green-100": "#" + S["green"],
        "text-default": "#" + S["fg"],
        "text-link": "#" + mix(primary, "FFFFFF", 0.18),
        "editor-text": "#" + S["fg"],
        "transparent": f"#{bg}00",
        "tab-file-color-mask-bg": f"#{bg}80",
        "search-match-bg": "#" + S["yellow"],
        "popup-completion-match-text": "#" + mix(primary, "FFFFFF", 0.15),
        "selection-bg-active": "#" + sel,
        "selection-bg-active-muted": "#" + sel_muted,
        "selection-bg-inactive": "#" + gray[30],
        "tab-selected-bg-active": "#" + sel_muted,
        "tab-selected-border-active": "#" + primary,
        "grad-hor-left": f"#{gray[30]}33",
        "grad-hor-right": f"#{gray[30]}4D",
        "grad-ver-top": f"#{gray[30]}1A",
        "grad-ver-bottom": f"#{gray[30]}80",
    })

    ui_text = json.dumps(src["ui"])
    ui_text = re.sub(r"#[0-9A-Fa-f]{8}\b|#[0-9A-Fa-f]{6}\b",
                     lambda m: remap_hex(m.group(0)), ui_text)
    ui = json.loads(ui_text)
    tw = "#" + gray[10]
    ui.update({
        "Island.borderColor": tw,
        "StatusBar.borderColor": "#00000000",
        "ToolWindow.Stripe.borderColor": "#00000000",
        "MainToolbar.borderColor": "#00000000",
        "EditorTabs.background": tw,
        "EditorTabs.underlinedTabBackground": "#" + sel_muted,
        "EditorTabs.underlinedBorderColor": "#" + primary,
        "EditorTabs.inactiveUnderlinedTabBorderColor": "#" + gray[70],
    })

    icons = copy.deepcopy(src.get("icons", {}))
    icons.setdefault("ColorPalette", {}).update({
        "Checkbox.Background.Selected": "#" + primary,
        "Checkbox.Border.Selected": "#" + primary,
        "Checkbox.Focus.Wide": "#" + primary,
        "Checkbox.Focus.Thin.Selected": "#" + mix(primary, "FFFFFF", 0.35),
        "Checkbox.Foreground.Selected": "#FFFFFF",
    })

    return {
        "name": var["name"],
        "dark": True,
        "author": "thequestionmarked (based on Vitesse by Anthony Fu)",
        "parentTheme": "Islands Dark",
        "editorScheme": var["name"],
        "colors": colors,
        "ui": ui,
        "icons": icons,
    }


# ================================================================ editor scheme
PLAIN, BOLD, ITALIC, BOLD_ITALIC = "0", "1", "2", "3"


def scheme_defs(S):
    fg_remap = {  # Rider Islands Dark palette -> Vitesse (covers JS/TS/CSS/XML/SQL...)
        "BDBDBD": S["fg"], "D0D0D0": S["fg"], "F0F0F0": S["fg"],
        "6C95EB": S["keyword"],
        "C191FF": S["class"], "E1BFFF": S["struct"],
        "39CC9B": S["function"],
        "66C3CC": S["variable"],
        "85C46C": S["comment"],
        "C9A26D": S["string"],
        "ED94C0": S["number"],
        "D688D4": S["escape"],
        "787878": S["punctuation"],
        "487D34": S["control"],
        "FFD49E": S["regex"],
        "7DF0C0": S["interface"],
        "ADEB96": S["cyan"],
        "FF5647": S["red"],
        "FF919C": S["magenta"], "E67281": S["magenta"],
        "D9B72B": S["yellow"], "F5D86A": S["yellow"], "FF9259": S["orange"],
        "406AC2": S["blue"], "7A5C43": S["orange"],
    }
    bg = S["bg"]
    bg_remap = {
        "191A1C": bg, "202424": S["bg_active"],
        "303030": S["raised"], "343434": S["raised"], "404040": S["raised2"],
        "424242": S["raised2"],
        "232E46": S["green_tint"],
        "29421F": blend(S["green"] + "50", bg), "21331A": blend(S["green"] + "30", bg),
        "28431B": blend(S["green"] + "50", bg),
        "4A2421": blend("ab595950", bg), "612722": blend("ab595970", bg),
        "502727": blend("ab595960", bg),
        "3A3070": blend(S["blue"] + "40", bg), "293A5F": blend(S["primary"] + "70", bg),
        "144238": blend("e6cc7744", bg), "187057": S["yellow"],
        "484012": blend("e6cc7733", bg), "8A7F23": S["yellow"],
        "422240": S["green_tint2"],
        "522750": blend("cb767640", bg), "913C8F": S["red"],
        "37300E": blend("e6cc7728", bg), "493927": blend("d4976c38", bg),
        "13362E": blend(S["primary"] + "38", bg), "#6B4C1B": blend("e6cc7750", bg),
        "6B4C1B": blend("e6cc7750", bg),
        "332C29": mix(bg, "C98A7D", 0.05), "4D2F6B": S["green_tint2"],
        "09434D": blend(S["cyan"] + "38", bg),
    }

    O = {}

    def fg(*names, color, font=PLAIN, **extra):
        for n in names:
            d = {"FOREGROUND": color, "FONT_TYPE": font}
            d.update(extra)
            O[n] = d

    # ---- language defaults (other languages inherit from these)
    fg("TEXT", color=S["fg"], BACKGROUND=bg)
    fg("DEFAULT_IDENTIFIER", "DEFAULT_LOCAL_VARIABLE", "DEFAULT_GLOBAL_VARIABLE",
       color=S["variable"])
    fg("DEFAULT_REASSIGNED_LOCAL_VARIABLE", color=S["variable"],
       EFFECT_COLOR=S["raised2"], EFFECT_TYPE="1")
    fg("DEFAULT_PARAMETER", "DEFAULT_REASSIGNED_PARAMETER", color=S["fg"])
    fg("DEFAULT_KEYWORD", color=S["keyword"], font=BOLD)
    fg("DEFAULT_STRING", color=S["string"])
    fg("DEFAULT_VALID_STRING_ESCAPE", color=S["escape"])
    fg("DEFAULT_NUMBER", color=S["number"])
    fg("DEFAULT_LINE_COMMENT", "DEFAULT_BLOCK_COMMENT", "DEFAULT_DOC_COMMENT",
       color=S["comment"], font=ITALIC)
    fg("DEFAULT_DOC_COMMENT_TAG", "DEFAULT_DOC_MARKUP", color=S["control"], font=ITALIC)
    fg("DEFAULT_DOC_COMMENT_TAG_VALUE", color=S["variable"], font=ITALIC)
    fg("DEFAULT_BRACES", "DEFAULT_BRACKETS", "DEFAULT_PARENTHS", "DEFAULT_COMMA",
       "DEFAULT_SEMICOLON", "DEFAULT_DOT", color=S["punctuation"])
    fg("DEFAULT_OPERATION_SIGN", color=S["operator"])
    fg("DEFAULT_CLASS_NAME", "DEFAULT_CLASS_REFERENCE", color=S["class"], font=ITALIC)
    fg("DEFAULT_INTERFACE_NAME", color=S["interface"], font=ITALIC)
    fg("DEFAULT_FUNCTION_DECLARATION", "DEFAULT_FUNCTION_CALL", "DEFAULT_INSTANCE_METHOD",
       "DEFAULT_STATIC_METHOD", color=S["function"], font=ITALIC)
    fg("DEFAULT_INSTANCE_FIELD", "DEFAULT_STATIC_FIELD", color=S["variable"])
    fg("DEFAULT_CONSTANT", color=S["constant"])
    fg("DEFAULT_METADATA", "DEFAULT_ATTRIBUTE", color=S["attribute"])
    fg("DEFAULT_LABEL", color=S["fg"])
    fg("DEFAULT_PREDEFINED_SYMBOL", color=S["keyword"])
    fg("DEFAULT_TAG", color=S["control"])
    fg("DEFAULT_ENTITY", color=S["constant"])

    # ---- C# (Rider / ReSharper keys)
    fg("ReSharper.CSHARP_KEYWORD", "ReSharper.CSHARP_ACCESSOR_IDENTIFIER",
       color=S["keyword"], font=BOLD)
    fg("ReSharper.CONTROL_FLOW_KEYWORD", "ReSharper.CONTROL_TRANSFER_KEYWORD",
       color=S["control"], font=BOLD)
    fg("ReSharper.CSHARP_PREPROCESSOR_KEYWORD", "ReSharper.PREPROCESSOR_KEYWORD",
       color=S["decorator"])
    fg("ReSharper.CSHARP_STRING", color=S["string"])
    fg("ReSharper.CSHARP_ESCAPE_CHARACTER_1", "ReSharper.CSHARP_ESCAPE_CHARACTER_2",
       "ReSharper.STRING_ESCAPE_CHARACTER_2", color=S["escape"])
    fg("ReSharper.CSHARP_NUMBER", color=S["number"])
    fg("ReSharper.CSHARP_LINE_COMMENT", "ReSharper.CSHARP_BLOCK_COMMENT",
       "ReSharper.CSHARP_DOC_COMMENT", color=S["comment"], font=ITALIC)
    fg("ReSharper.CSHARP_DOC_COMMENT_TAG_NAME", color=S["control"], font=ITALIC)
    fg("ReSharper.CSHARP_DOC_COMMENT_ATTRIBUTE", color=S["property"], font=ITALIC)
    fg("ReSharper.CSHARP_DOC_COMMENT_ATTRIBUTE_VALUE", color=S["string"], font=ITALIC)
    fg("ReSharper.CSHARP_BRACES", "ReSharper.CSHARP_BRACKETS", "ReSharper.CSHARP_PARENTHESES",
       "ReSharper.CSHARP_COMMA", "ReSharper.CSHARP_SEMICOLON", "ReSharper.CSHARP_DOT",
       color=S["punctuation"])
    fg("ReSharper.CSHARP_OPERATOR_SIGN", "ReSharper.CSHARP_OVERFLOW_CHECKED_OPERATION",
       color=S["operator"])
    fg("ReSharper.CSHARP_OVERLOADED_OPERATOR", color=S["function"])
    fg("ReSharper.CSHARP_NAMESPACE_IDENTIFIER", "ReSharper.NAMESPACE_IDENTIFIER",
       color=S["namespace"])
    fg("ReSharper.CSHARP_CLASS_IDENTIFIER", "ReSharper.CSHARP_STATIC_CLASS_IDENTIFIER",
       "ReSharper.STATIC_CLASS_IDENTIFIER", "ReSharper.CSHARP_RECORD_IDENTIFIER",
       "ReSharper.ST_TYPE", color=S["class"], font=ITALIC)
    fg("ReSharper.CSHARP_STRUCT_IDENTIFIER", "ReSharper.STRUCT_IDENTIFIER",
       "ReSharper.CSHARP_RECORD_STRUCT_IDENTIFIER", "ReSharper.CSHARP_ENUM_IDENTIFIER",
       "ReSharper.ENUM_IDENTIFIER", color=S["struct"], font=ITALIC)
    fg("ReSharper.CSHARP_INTERFACE_IDENTIFIER", "ReSharper.CSHARP_DELEGATE_IDENTIFIER",
       "ReSharper.DELEGATE_IDENTIFIER", color=S["interface"], font=ITALIC)
    fg("ReSharper.CSHARP_TYPE_PARAMETER_IDENTIFIER", "ReSharper.TYPE_PARAMETER_IDENTIFIER",
       color=S["interface"])
    fg("ReSharper.CSHARP_METHOD_IDENTIFIER", "ReSharper.CSHARP_STATIC_METHOD_IDENTIFIER",
       "ReSharper.CSHARP_LOCAL_FUNCTION_IDENTIFIER", "ReSharper.CSHARP_EXTENSION_METHOD_IDENTIFIER",
       "ReSharper.EXTENSION_METHOD_IDENTIFIER", "ReSharper.ST_METHOD",
       color=S["function"], font=ITALIC)
    fg("ReSharper.CSHARP_PROPERTY_IDENTIFIER", "ReSharper.CSHARP_STATIC_PROPERTY_IDENTIFIER",
       "ReSharper.PROPERTY_IDENTIFIER", color=S["property"], font=ITALIC)
    fg("ReSharper.CSHARP_TUPLE_COMPONENT_NAME", color=S["property"])
    fg("ReSharper.CSHARP_FIELD_IDENTIFIER", "ReSharper.CSHARP_STATIC_FIELD_IDENTIFIER",
       color=S["variable"])
    fg("ReSharper.CSHARP_CONSTANT_IDENTIFIER", color=S["constant"])
    fg("ReSharper.CSHARP_EVENT_IDENTIFIER", "ReSharper.EVENT_IDENTIFIER",
       color=S["event"], font=ITALIC)
    fg("ReSharper.CSHARP_LOCAL_VARIABLE_IDENTIFIER", color=S["variable"])
    fg("ReSharper.CSHARP_MUTABLE_LOCAL_VARIABLE_IDENTIFIER",
       "ReSharper.MUTABLE_LOCAL_VARIABLE_IDENTIFIER",
       color=S["variable"], EFFECT_COLOR=S["raised2"], EFFECT_TYPE="1")
    fg("ReSharper.CSHARP_PARAMETER_IDENTIFIER", color=S["fg"])
    fg("ReSharper.CSHARP_LATE_BOUND_IDENTIFIER", "ReSharper.LATE_BOUND_IDENTIFIER",
       color=S["fg_secondary"], font=ITALIC)
    fg("ReSharper.FORMAT_STRING_ITEM", "ReSharper.FORMAT_STRING_ITEM_2", color=S["control"])
    fg("ReSharper.CSHARP_PREPROCESSOR_INACTIVE_BRANCH", "ReSharper.INACTIVE_PREPROCESSOR_BRANCH",
       color=S["ignored"])

    # ---- JS / TS / JSON / XML touches
    fg("ReSharper.JS_PROPERTY_IDENTIFIER", "ReSharper.JS_UNKNOWN_PROPERTY_IDENTIFIER",
       "JSON.PROPERTY_KEY", "YAML_SCALAR_KEY", color=S["property"])
    fg("HTML_TAG_NAME", "XML_TAG_NAME", "HTML_TAG", "XML_TAG", color=S["control"])
    fg("HTML_ATTRIBUTE_NAME", "XML_ATTRIBUTE_NAME", color=S["variable"])
    fg("JS.MODULE_NAME", "TS.MODULE_NAME", color=S["namespace"])

    # ---- chrome
    O["DIFF_INSERTED"] = {"BACKGROUND": blend(S["green"] + "50", bg), "ERROR_STRIPE_COLOR": S["green"]}
    O["DIFF_MODIFIED"] = {"BACKGROUND": blend(S["blue"] + "40", bg), "ERROR_STRIPE_COLOR": S["blue"]}
    O["DIFF_DELETED"] = {"BACKGROUND": S["raised2"], "ERROR_STRIPE_COLOR": S["punctuation"]}
    O["DIFF_CONFLICT"] = {"BACKGROUND": blend("ab595950", bg), "ERROR_STRIPE_COLOR": S["red"]}
    O["MATCHED_BRACE_ATTRIBUTES"] = {"BACKGROUND": S["green_tint2"], "FONT_TYPE": BOLD}
    O["IDENTIFIER_UNDER_CARET_ATTRIBUTES"] = {"BACKGROUND": S["green_tint"],
                                             "ERROR_STRIPE_COLOR": blend(S["primary"] + "90", bg)}
    O["WRITE_IDENTIFIER_UNDER_CARET_ATTRIBUTES"] = {"BACKGROUND": S["green_tint2"],
                                                   "ERROR_STRIPE_COLOR": S["primary"]}
    O["INLINE_PARAMETER_HINT"] = {"BACKGROUND": S["raised"], "FOREGROUND": S["punctuation"], "FONT_TYPE": PLAIN}
    O["INLINE_PARAMETER_HINT_CURRENT"] = {"BACKGROUND": S["raised2"], "FOREGROUND": S["fg_secondary"], "FONT_TYPE": PLAIN}
    O["INLINE_PARAMETER_HINT_HIGHLIGHTED"] = {"BACKGROUND": S["green_tint"], "FOREGROUND": S["fg"]}
    O["FOLDED_TEXT_ATTRIBUTES"] = {"BACKGROUND": S["raised"], "EFFECT_COLOR": S["raised2"], "FOREGROUND": S["punctuation"]}
    O["TODO_DEFAULT_ATTRIBUTES"] = {"FOREGROUND": S["yellow"], "FONT_TYPE": BOLD_ITALIC, "ERROR_STRIPE_COLOR": S["yellow"]}
    O["BREADCRUMBS_DEFAULT"] = {"FOREGROUND": S["fg_secondary"]}
    O["BREADCRUMBS_CURRENT"] = {"FOREGROUND": S["fg"], "BACKGROUND": S["raised"]}
    O["BREADCRUMBS_HOVERED"] = {"FOREGROUND": S["fg"], "BACKGROUND": S["raised"]}
    O["BREADCRUMBS_INACTIVE"] = {"FOREGROUND": S["ignored"]}
    for nm, col in {
        "BLACK": "393A34", "RED": S["red"], "GREEN": S["green"], "YELLOW": S["yellow"],
        "BLUE": S["blue"], "MAGENTA": S["magenta"], "CYAN": S["cyan"], "WHITE": "DBD7CA",
        "DARKGRAY": "777777", "RED_BRIGHT": S["red"], "GREEN_BRIGHT": S["green"],
        "YELLOW_BRIGHT": S["yellow"], "BLUE_BRIGHT": S["blue"], "MAGENTA_BRIGHT": S["magenta"],
        "CYAN_BRIGHT": S["cyan"], "GRAY": "AAAAAA",
    }.items():
        O[f"CONSOLE_{nm}_OUTPUT"] = {"FOREGROUND": col}
    O["CONSOLE_NORMAL_OUTPUT"] = {"FOREGROUND": S["fg"]}
    O["CONSOLE_ERROR_OUTPUT"] = {"FOREGROUND": S["red"]}
    O["CONSOLE_SYSTEM_OUTPUT"] = {"FOREGROUND": S["fg_secondary"]}
    O["CONSOLE_USER_INPUT"] = {"FOREGROUND": S["green"], "FONT_TYPE": ITALIC}

    colors = {
        "CARET_COLOR": "DBD7CA",
        "CARET_ROW_COLOR": S["bg_active"],
        "CONSOLE_BACKGROUND_KEY": bg,
        "DOCUMENTATION_COLOR": S["bg_active"],
        "GUTTER_BACKGROUND": bg,
        "LOOKUP_COLOR": S["bg_active"],
        "LINE_NUMBERS_COLOR": S["ignored"],
        "LINE_NUMBER_ON_CARET_ROW_COLOR": S["fg_active"],
        "INDENT_GUIDE": blend("ffffff15", bg),
        "SELECTED_INDENT_GUIDE": blend("ffffff30", bg),
        "RIGHT_MARGIN_COLOR": S["raised"],
        "METHOD_SEPARATORS_COLOR": S["raised2"],
        "TEARLINE_COLOR": S["raised2"],
        "SELECTED_TEARLINE_COLOR": blend("ffffff28", bg),
        "FOLDED_TEXT_BORDER_COLOR": S["raised2"],
        "WHITESPACES": blend("ffffff20", bg),
        "SOFT_WRAP_SIGN_COLOR": S["punctuation"],
        "SELECTION_BACKGROUND": blend(S["primary"] + "30", mix(bg, "FFFFFF", 0.06)),
        "ADDED_LINES_COLOR": S["green"],
        "MODIFIED_LINES_COLOR": S["blue"],
        "DELETED_LINES_COLOR": S["red"],
        "WHITESPACES_MODIFIED_LINES_COLOR": blend("e6cc7730", bg),
        "INFORMATION_HINT": S["raised"],
        "QUESTION_HINT": blend("e6cc7728", bg),
        "ERROR_HINT": blend("cb767638", bg),
        "NOTIFICATION_BACKGROUND": S["raised"],
        "READONLY_BACKGROUND": mix(bg, "FFFFFF", 0.02),
        "READONLY_FRAGMENT_BACKGROUND": S["raised"],
        "ANNOTATIONS_COLOR": S["fg_secondary"],
        "MnemonicIcon.borderColor": bg,
        "MnemonicIcon.foreground": bg,
        "MnemonicIcon.background": S["yellow"],
        "BookmarkIcon.background": S["yellow"],
        "VCS_ANNOTATIONS_COLOR_1": blend(S["green"] + "30", bg),
        "VCS_ANNOTATIONS_COLOR_2": blend(S["green"] + "18", bg),
        "VCS_ANNOTATIONS_COLOR_3": S["raised"],
        "VCS_ANNOTATIONS_COLOR_4": blend("cb767618", bg),
        "VCS_ANNOTATIONS_COLOR_5": blend("cb767630", bg),
    }
    scroll = {
        "background": bg, "trackColor": bg + "00", "hoverTrackColor": bg + "00",
        "thumbColor": "DEDCD520", "thumbBorderColor": "DEDCD520",
        "hoverThumbColor": "DEDCD540", "hoverThumbBorderColor": "DEDCD540",
    }
    return fg_remap, bg_remap, O, colors, scroll


def norm(v):
    return v.upper().lstrip("#") if v else v


def build_scheme(var, S):
    fg_remap, bg_remap, O, color_over, scroll = scheme_defs(S)
    tree = ET.parse(RIDER_SCHEME)
    root = tree.getroot()
    root.set("name", var["name"])
    root.set("parent_scheme", "Darcula")

    colors = root.find("colors")
    existing = {o.get("name"): o for o in colors}
    for k, v in color_over.items():
        if k in existing:
            existing[k].set("value", v)
        else:
            ET.SubElement(colors, "option", name=k, value=v)
    for o in colors:
        n = o.get("name")
        if n.startswith("ScrollBar."):
            suf = n.split(".")[-1]
            if suf in scroll:
                o.set("value", scroll[suf])

    attrs = root.find("attributes")
    by_name = {o.get("name"): o for o in attrs}
    for o in attrs:
        val = o.find("value")
        if val is None:
            continue
        for x in val:
            key, raw = x.get("name"), x.get("value")
            v = norm(raw)
            if key in ("FOREGROUND", "EFFECT_COLOR") and v in fg_remap:
                x.set("value", fg_remap[v])
            elif key in ("BACKGROUND", "ERROR_STRIPE_COLOR"):
                if raw in bg_remap:
                    x.set("value", bg_remap[raw])
                elif v in bg_remap:
                    x.set("value", bg_remap[v])
    # comments in other languages: italic like the C#/default ones
    for o in attrs:
        val = o.find("value")
        if val is None:
            continue
        d = {x.get("name"): x for x in val}
        if "FOREGROUND" in d and d["FOREGROUND"].get("value") == S["comment"]:
            if "FONT_TYPE" in d:
                d["FONT_TYPE"].set("value", ITALIC)
            else:
                ET.SubElement(val, "option", name="FONT_TYPE", value=ITALIC)

    for name, d in O.items():
        o = by_name.get(name)
        if o is None:
            o = ET.SubElement(attrs, "option", name=name)
            by_name[name] = o
        o.attrib.pop("baseAttributes", None)
        for ch in list(o):
            o.remove(ch)
        val = ET.SubElement(o, "value")
        for k in sorted(d):
            ET.SubElement(val, "option", name=k, value=d[k])

    items = sorted(list(attrs), key=lambda e: e.get("name"))
    for e in list(attrs):
        attrs.remove(e)
    attrs.extend(items)
    ET.indent(tree, space="  ")
    return tree


# ================================================================ main
def main():
    res = OUT / "src" / "main" / "resources"
    (res / "colorSchemes").mkdir(parents=True, exist_ok=True)
    (res / "themes").mkdir(parents=True, exist_ok=True)
    palettes = {}
    for key, var in VARIANTS.items():
        S = make_palette(var)
        palettes[key] = S
        theme = build_ui_theme(var, S)
        (res / "themes" / f"{var['id'].replace('-', '_')}.theme.json").write_text(
            json.dumps(theme, indent=2, ensure_ascii=False) + "\n")
        build_scheme(var, S).write(res / "colorSchemes" / f"{var['file']}.xml", encoding="unicode")
        main_win = var["gray"][30]
        print(f"{var['name']}: main/tool contrast {contrast(main_win, var['bg']):.2f}")
        worst = min((contrast(S[k], var["bg"]), k) for k in
                    ("keyword", "control", "function", "class", "struct", "interface", "namespace",
                     "constant", "variable", "property", "string", "number", "comment", "fg"))
        print(f"  lowest text contrast: {worst[1]} {worst[0]:.2f}")
    (OUT / "palettes.json").write_text(json.dumps(palettes, indent=2))


if __name__ == "__main__":
    main()
