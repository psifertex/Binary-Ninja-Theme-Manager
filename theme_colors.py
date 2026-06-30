"""Resolve `.bntheme` colors to QColor without applying the theme globally (BN
exposes no API to read an inactive theme, so we reimplement ui/shared/theme.cpp).

Values are flat prefix expressions that nest, e.g.
  ["~", "+", "backgroundDark", "background", "green", 48]
  "+"  -> per-channel average           (avgColor, theme.cpp:29)
  "~"  -> weighted mix, weight 0..255   (mixColor, theme.cpp:35)
plus [R,G,B] / [R,G,B,A], an alias name, or a "#rrggbb" string.
"""

from binaryninja import log_error
from PySide6.QtGui import QColor

# Prefer BN's own color math for bit-exact parity; fall back to local copies when
# binaryninjaui isn't importable (e.g. standalone testing).
try:
    from binaryninjaui import avgColor as avg_color, mixColor as mix_color
except Exception:
    def avg_color(a, b):
        # RGB-only average; BN's avgColor drops alpha (result is opaque).
        return QColor(
            (a.red() + b.red()) // 2,
            (a.green() + b.green()) // 2,
            (a.blue() + b.blue()) // 2,
        )

    def mix_color(a, b, weight):
        w = max(0, min(255, int(weight)))
        return QColor(
            (a.red() * (255 - w) + b.red() * w) // 255,
            (a.green() * (255 - w) + b.green() * w) // 255,
            (a.blue() * (255 - w) + b.blue() * w) // 255,
            (a.alpha() * (255 - w) + b.alpha() * w) // 255,
        )


# Fallbacks for keys a theme omits, from BN's built-in dark default (theme.cpp).
_DEFAULTS = {
    "content": QColor(224, 224, 224),
    "background": QColor(42, 42, 42),
    "addressColor": QColor(162, 217, 175),
    "instructionColor": QColor(237, 223, 179),
    "registerColor": QColor(224, 224, 224),
    "numberColor": QColor(162, 217, 175),
    "codeSymbolColor": QColor(128, 198, 233),
    "dataSymbolColor": QColor(142, 230, 237),
    "localVariableColor": QColor(224, 224, 224),
    "stackVariableColor": QColor(193, 220, 199),       # avg(green, content)
    "importColor": QColor(237, 189, 129),
    "stringColor": QColor(218, 196, 209),
    "commentColor": QColor(218, 196, 209),
    "annotationColor": QColor(218, 196, 209),
    "typeNameColor": QColor(237, 189, 129),
    "fieldNameColor": QColor(176, 221, 228),
    "keywordColor": QColor(237, 223, 179),
    "nameSpaceColor": QColor(128, 198, 233),
    "gotoLabelColor": QColor(128, 198, 233),
    "opcodeColor": QColor(144, 144, 144),
    "operationColor": QColor(137, 164, 177),           # mix(disabled, blue, 96)
    "uncertainColor": QColor(144, 144, 144),
    "linearDisassemblyBlockColor": QColor(42, 42, 42),
    "linearDisassemblyFunctionHeaderColor": QColor(58, 58, 58),
    "linearDisassemblyNoteColor": QColor(45, 58, 49),
    "linearDisassemblySeparatorColor": QColor(144, 144, 144),
    "graphBackgroundDarkColor": QColor(42, 42, 42),
    "graphBackgroundLightColor": QColor(42, 42, 42),
    "graphNodeDarkColor": QColor(74, 74, 74),
    "graphNodeLightColor": QColor(74, 74, 74),
    "graphNodeOutlineColor": QColor(144, 144, 144),
    "trueBranchColor": QColor(162, 217, 175),
    "falseBranchColor": QColor(222, 143, 151),
    "unconditionalBranchColor": QColor(128, 198, 233),
    "altTrueBranchColor": QColor(128, 198, 233),
    "altFalseBranchColor": QColor(237, 189, 129),
    "altUnconditionalBranchColor": QColor(224, 224, 224),
}


# Token-type name -> theme-color key, mirroring the getTokenColor() switch in
# ui/shared/theme.cpp:3229-3295. A value of None means "use the default text
# color" (BN falls back to QPalette::WindowText for those).
TOKEN_COLOR_MAP = {
    "TextToken": None,
    "OperandSeparatorToken": None,
    "AddressDisplayToken": "addressColor",
    "InstructionToken": "instructionColor",
    "RegisterToken": "registerColor",
    "IntegerToken": "numberColor",
    "PossibleAddressToken": "numberColor",
    "FloatingPointToken": "numberColor",
    "CodeSymbolToken": "codeSymbolColor",
    "DataSymbolToken": "dataSymbolColor",
    "LocalVariableToken": "localVariableColor",
    "StackVariableToken": "stackVariableColor",
    "ImportToken": "importColor",
    "StringToken": "stringColor",
    "CommentToken": "commentColor",
    "AnnotationToken": "annotationColor",
    "TypeNameToken": "typeNameColor",
    "FieldNameToken": "fieldNameColor",
    "KeywordToken": "keywordColor",
    "NameSpaceToken": "nameSpaceColor",
    "GotoLabelToken": "gotoLabelColor",
    "OpcodeToken": "opcodeColor",
    "OperationToken": "operationColor",
    # Hex dump: regular byte/text tokens fall through to WindowText in BN; only
    # invalid bytes get a dedicated color (UncertainColor).
    "HexDumpByteValueToken": None,
    "HexDumpTextToken": None,
    "HexDumpInvalidByteToken": "uncertainColor",
}


class ThemeColorResolver:
    """Resolves `.bntheme` color values to QColor without touching the global theme."""

    def __init__(self, theme_json):
        self.name = theme_json.get("name", "Unknown")
        self.colors = theme_json.get("colors", {}) or {}
        self.palette = theme_json.get("palette", {}) or {}
        self.theme_colors = theme_json.get("theme-colors", {}) or {}
        self._alias_cache = {}
        self._resolving = set()  # cycle guard for malformed themes

    def _resolve_alias(self, name):
        if name in self._alias_cache:
            return self._alias_cache[name]
        if name in self._resolving:
            return _DEFAULTS.get("content")  # broken cycle
        self._resolving.add(name)
        try:
            if name in self.colors:
                color = self._parse_value(self.colors[name])
            elif name.startswith("#"):
                color = QColor(name)
            else:
                color = QColor(name)  # try Qt named color
                if not color.isValid():
                    color = _DEFAULTS.get(name, _DEFAULTS["content"])
        finally:
            self._resolving.discard(name)
        self._alias_cache[name] = color
        return color

    def _parse_value(self, value):
        """Resolve a raw theme value (string / [R,G,B] / RPN list) to a QColor."""
        if isinstance(value, str):
            return self._resolve_alias(value)
        if isinstance(value, list) and value:
            if isinstance(value[0], str) and value[0] in ("+", "~"):
                color, _ = self._consume(value, 0)
                return color
            if all(isinstance(x, (int, float)) for x in value):
                vals = [max(0, min(255, int(x))) for x in value]
                if len(vals) >= 4:
                    return QColor(vals[0], vals[1], vals[2], vals[3])
                if len(vals) == 3:
                    return QColor(vals[0], vals[1], vals[2])
        return _DEFAULTS["content"]

    def _consume(self, stream, i):
        """Consume one color expression from a flat prefix stream.

        Returns (QColor, next_index). Ports ParseColor, theme.cpp:339-387.
        """
        tok = stream[i]
        if tok == "+":
            a, i = self._consume(stream, i + 1)
            b, i = self._consume(stream, i)
            return avg_color(a, b), i
        if tok == "~":
            a, i = self._consume(stream, i + 1)
            b, i = self._consume(stream, i)
            weight = stream[i] if i < len(stream) else 0
            return mix_color(a, b, weight), i + 1
        if isinstance(tok, list):
            return self._parse_value(tok), i + 1
        if isinstance(tok, str):
            return self._resolve_alias(tok), i + 1
        if isinstance(tok, (int, float)):
            v = max(0, min(255, int(tok)))
            return QColor(v, v, v), i + 1
        return _DEFAULTS["content"], i + 1

    def resolve(self, theme_color_key):
        """Resolve a `theme-colors` key (e.g. 'instructionColor') to a QColor."""
        if theme_color_key in self.theme_colors:
            try:
                return self._parse_value(self.theme_colors[theme_color_key])
            except Exception as e:
                log_error(f"[ThemeManager] Failed to resolve '{theme_color_key}': {e}")
        return _DEFAULTS.get(theme_color_key, _DEFAULTS["content"])

    def default_text(self):
        """Default text color (QPalette::WindowText), as BN uses for unmapped tokens."""
        if "WindowText" in self.palette:
            try:
                return self._parse_value(self.palette["WindowText"])
            except Exception:
                pass
        if "content" in self.colors:
            return self._resolve_alias("content")
        return _DEFAULTS["content"]

    def view_background(self):
        """The linear view canvas background (QPalette::Base).

        Used behind data variables and raw hex dumps, which in BN render on the
        plain view background rather than the lighter linearDisassemblyBlockColor.
        """
        if "Base" in self.palette:
            try:
                return self._parse_value(self.palette["Base"])
            except Exception:
                pass
        if "background" in self.colors:
            return self._resolve_alias("background")
        return _DEFAULTS["background"]

    def token_color(self, token_type_name):
        """Resolve the color for a fake token type name via TOKEN_COLOR_MAP."""
        key = TOKEN_COLOR_MAP.get(token_type_name, None)
        if key is None:
            return self.default_text()
        return self.resolve(key)

    def background(self, key="linearDisassemblyBlockColor"):
        """Resolve a section background color (defaults to the disassembly block)."""
        return self.resolve(key)
