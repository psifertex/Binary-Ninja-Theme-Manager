"""Paints representative linear-view and graph-view samples from a parsed theme,
without touching Binary Ninja's global theme. The two views are separate widgets
so the dialog can place a native splitter between them."""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QFontDatabase, QFontMetrics, QPen, QBrush, QLinearGradient
)
from PySide6.QtCore import QSize, Qt, QRect, QPointF


_SECTION_BG = {
    "header": "linearDisassemblyFunctionHeaderColor",
    "block": "linearDisassemblyBlockColor",
    "note": "linearDisassemblyNoteColor",
}


def _resolve_section_bg(resolver, kind):
    # "data" uses the view canvas (QPalette::Base), matching how BN renders data
    # variables / hex dumps rather than the lighter linearDisassemblyBlockColor.
    if kind == "data":
        return resolver.view_background()
    return resolver.background(_SECTION_BG[kind])


SECTIONS = [
    {
        "bg": "header",
        "lines": [
            [("KeywordToken", "int64_t"), ("TextToken", " "),
             ("CodeSymbolToken", "main"), ("TextToken", "("),
             ("KeywordToken", "int32_t"), ("TextToken", " "),
             ("LocalVariableToken", "argc"), ("OperandSeparatorToken", ", "),
             ("KeywordToken", "char**"), ("TextToken", " "),
             ("LocalVariableToken", "argv"), ("TextToken", ")")],
        ],
    },
    {
        "bg": "block",
        "lines": [
            [("AddressDisplayToken", "00401000"), ("TextToken", "  "),
             ("OpcodeToken", "55                 "),
             ("InstructionToken", "push"), ("TextToken", "    "),
             ("RegisterToken", "rbp")],
            [("AddressDisplayToken", "00401001"), ("TextToken", "  "),
             ("OpcodeToken", "4889e5             "),
             ("InstructionToken", "mov"), ("TextToken", "     "),
             ("RegisterToken", "rbp"), ("OperandSeparatorToken", ", "),
             ("RegisterToken", "rsp")],
            [("AddressDisplayToken", "00401004"), ("TextToken", "  "),
             ("OpcodeToken", "488b45e8           "),
             ("InstructionToken", "mov"), ("TextToken", "     "),
             ("RegisterToken", "rax"), ("OperandSeparatorToken", ", "),
             ("KeywordToken", "qword"), ("TextToken", " ["),
             ("RegisterToken", "rbp"), ("TextToken", "-"),
             ("IntegerToken", "0x18"), ("TextToken", " "),
             ("StackVariableToken", "{var_20}"), ("TextToken", "]")],
            [("AddressDisplayToken", "0040100b"), ("TextToken", "  "),
             ("OpcodeToken", "bee03f4000         "),
             ("InstructionToken", "mov"), ("TextToken", "     "),
             ("RegisterToken", "esi"), ("OperandSeparatorToken", ", "),
             ("PossibleAddressToken", "0x403fe0"), ("TextToken", "  "),
             ("StringToken", '{"hello, world"}')],
            [("AddressDisplayToken", "00401010"), ("TextToken", "  "),
             ("OpcodeToken", "e86ce6ffff         "),
             ("InstructionToken", "call"), ("TextToken", "    "),
             ("ImportToken", "printf"), ("TextToken", "          "),
             ("CommentToken", "; print message")],
        ],
    },
    {
        "bg": "data",
        "lines": [
            [("DataSymbolToken", "data_403fe0"), ("OperandSeparatorToken", ":  "),
             ("KeywordToken", "char"), ("TextToken", " "),
             ("FieldNameToken", "msg"), ("OperandSeparatorToken", " = "),
             ("StringToken", '"hello, world"')],
            [("AddressDisplayToken", "00403fe0"), ("TextToken", "  "),
             ("HexDumpByteValueToken", "68 65 6c 6c 6f 2c 20 77"),
             ("TextToken", "  "), ("HexDumpTextToken", "hello, w")],
            [("AddressDisplayToken", "00403fe8"), ("TextToken", "  "),
             ("HexDumpByteValueToken", "6f 72 6c 64 00 "),
             ("HexDumpInvalidByteToken", "?? ??"),
             ("TextToken", "  "), ("HexDumpTextToken", "orld.··")],
        ],
    },
    {
        "bg": "note",
        "lines": [
            [("CommentToken", "; ---- function epilogue ----")],
            [("AnnotationToken", "{ stack frame: 0x20 bytes }")],
        ],
    },
]

# Graph-view sample: a loop (entry -> header -> body -> back to header, exit).
# Lines show offset + opcode bytes + disassembly, as in BN's graph view. Only the
# function entry carries a symbol label; BN hides loc_ block labels by default.
_FG_NODE_A = [
    [("CodeSymbolToken", "_main"), ("TextToken", ":")],
    [("AddressDisplayToken", "00401000"), ("TextToken", "  "),
     ("OpcodeToken", "55          "),
     ("InstructionToken", "push"), ("TextToken", "   "), ("RegisterToken", "rbp")],
    [("AddressDisplayToken", "00401001"), ("TextToken", "  "),
     ("OpcodeToken", "4889e5      "),
     ("InstructionToken", "mov"), ("TextToken", "    "),
     ("RegisterToken", "rbp"), ("OperandSeparatorToken", ", "),
     ("RegisterToken", "rsp")],
]
_FG_NODE_B = [
    [("AddressDisplayToken", "00401010"), ("TextToken", "  "),
     ("OpcodeToken", "83fe0b      "),
     ("InstructionToken", "cmp"), ("TextToken", "    "),
     ("RegisterToken", "esi"), ("OperandSeparatorToken", ", "),
     ("IntegerToken", "0xb")],
    [("AddressDisplayToken", "00401013"), ("TextToken", "  "),
     ("OpcodeToken", "7f2b        "),
     ("InstructionToken", "jg"), ("TextToken", "     "),
     ("PossibleAddressToken", "0x401040")],
]
_FG_NODE_C = [
    [("AddressDisplayToken", "00401020"), ("TextToken", "  "),
     ("OpcodeToken", "e86ce6ffff  "),
     ("InstructionToken", "call"), ("TextToken", "   "), ("ImportToken", "printf")],
    [("AddressDisplayToken", "00401025"), ("TextToken", "  "),
     ("OpcodeToken", "ffc6        "),
     ("InstructionToken", "inc"), ("TextToken", "    "), ("RegisterToken", "esi")],
]
_FG_NODE_D = [
    [("AddressDisplayToken", "00401040"), ("TextToken", "  "),
     ("OpcodeToken", "31c0        "),
     ("InstructionToken", "xor"), ("TextToken", "    "),
     ("RegisterToken", "eax"), ("OperandSeparatorToken", ", "),
     ("RegisterToken", "eax")],
    [("AddressDisplayToken", "00401043"), ("TextToken", "  "),
     ("OpcodeToken", "c3          "),
     ("InstructionToken", "ret")],
]

_PAD_X = 10
_PAD_Y = 6
_SECTION_GAP = 2
_NODE_PAD = 7
_FG_TOP_GAP = 22
_FG_ROW_GAP = 54
_FG_BOTTOM_GAP = 22
_FG_COL_GAP = 50
_FG_BACK_LANE = 14
_FG_SCALE_X = 0.90
_FG_SCALE_Y = 0.85


class _PreviewBase(QWidget):
    def __init__(self, resolver=None, parent=None):
        super().__init__(parent)
        self._resolver = resolver
        self._font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self._font.setPointSize(13)
        self._metrics = QFontMetrics(self._font)

    def set_resolver(self, resolver):
        self._resolver = resolver
        self.update()

    def _line_width(self, line):
        return sum(self._metrics.horizontalAdvance(t) for _, t in line)

    def _draw_tokens(self, painter, r, line, x, baseline):
        for token_type, text in line:
            painter.setPen(r.token_color(token_type))
            painter.drawText(x, baseline, text)
            x += self._metrics.horizontalAdvance(text)
        return x

    def _paint_placeholder(self, painter):
        painter.fillRect(self.rect(), Qt.darkGray)
        painter.setPen(Qt.white)
        painter.drawText(self.rect(), Qt.AlignCenter, "Select a theme to preview")


class LinearPreview(_PreviewBase):
    def _content_height(self):
        line_h = self._metrics.height()
        total_lines = sum(len(s["lines"]) for s in SECTIONS)
        n = len(SECTIONS)
        return total_lines * line_h + n * 2 * _PAD_Y + (n - 1) * _SECTION_GAP

    def sizeHint(self):
        widest = max((self._line_width(l) for s in SECTIONS for l in s["lines"]),
                     default=0)
        return QSize(widest + 2 * _PAD_X, self._content_height())

    def minimumSizeHint(self):
        return QSize(0, self._content_height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self._font)
        if self._resolver is None:
            self._paint_placeholder(painter)
            painter.end()
            return

        r = self._resolver
        line_h = self._metrics.height()
        ascent = self._metrics.ascent()
        width = self.width()
        painter.fillRect(self.rect(), r.view_background())

        y = 0
        for i, section in enumerate(SECTIONS):
            n = len(section["lines"])
            sect_h = n * line_h + 2 * _PAD_Y
            painter.fillRect(0, y, width, sect_h, _resolve_section_bg(r, section["bg"]))
            ty = y + _PAD_Y
            for line in section["lines"]:
                self._draw_tokens(painter, r, line, _PAD_X, ty + ascent)
                ty += line_h
            y += sect_h
            if i < len(SECTIONS) - 1:
                painter.fillRect(0, y, width, _SECTION_GAP,
                                 r.resolve("linearDisassemblySeparatorColor"))
                y += _SECTION_GAP
        painter.end()


class GraphPreview(_PreviewBase):
    def _node_width(self, lines):
        return max(self._line_width(l) for l in lines) + 2 * _NODE_PAD

    def _node_height(self, lines):
        return len(lines) * self._metrics.height() + 2 * _NODE_PAD

    def _flowgraph_height(self):
        return (_FG_TOP_GAP + self._node_height(_FG_NODE_A) + _FG_ROW_GAP
                + self._node_height(_FG_NODE_B) + _FG_ROW_GAP
                + max(self._node_height(_FG_NODE_C), self._node_height(_FG_NODE_D))
                + _FG_BOTTOM_GAP)

    def _flowgraph_width(self):
        cw = self._node_width(_FG_NODE_C)
        dw = self._node_width(_FG_NODE_D)
        row = cw + _FG_COL_GAP + dw
        return max(self._node_width(_FG_NODE_A), self._node_width(_FG_NODE_B),
                   row) + 2 * _PAD_X

    def _scaled_height(self):
        return int(self._flowgraph_height() * _FG_SCALE_Y)

    def sizeHint(self):
        return QSize(int(self._flowgraph_width() * _FG_SCALE_X), self._scaled_height())

    def minimumSizeHint(self):
        return QSize(0, self._scaled_height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self._font)
        if self._resolver is None:
            self._paint_placeholder(painter)
            painter.end()
            return

        r = self._resolver
        width = self.width()
        height = self.height()
        grad = QLinearGradient(0, 0, 0, height)
        grad.setColorAt(0.0, r.resolve("graphBackgroundLightColor"))
        grad.setColorAt(1.0, r.resolve("graphBackgroundDarkColor"))
        painter.fillRect(0, 0, width, height, QBrush(grad))

        # Compact the graph to 90% width / 85% height, centered horizontally.
        painter.save()
        painter.translate(width * (1 - _FG_SCALE_X) / 2.0, 0)
        painter.scale(_FG_SCALE_X, _FG_SCALE_Y)
        self._paint_flowgraph(painter, r, 0, 0, width)
        painter.restore()
        painter.end()

    def _paint_flowgraph(self, painter, r, rx, ry, rw):
        aw, ah = self._node_width(_FG_NODE_A), self._node_height(_FG_NODE_A)
        bw, bh = self._node_width(_FG_NODE_B), self._node_height(_FG_NODE_B)
        cw, ch = self._node_width(_FG_NODE_C), self._node_height(_FG_NODE_C)
        dw, dh = self._node_width(_FG_NODE_D), self._node_height(_FG_NODE_D)

        cx_mid = rx + rw // 2
        ax, ay = cx_mid - aw // 2, ry + _FG_TOP_GAP
        bx, by = cx_mid - bw // 2, ay + ah + _FG_ROW_GAP
        cy = by + bh + _FG_ROW_GAP
        cx = cx_mid - (cw + _FG_COL_GAP + dw) // 2
        cx = max(cx, rx + _FG_BACK_LANE + 4)
        dx = cx + cw + _FG_COL_GAP

        true_c = r.resolve("trueBranchColor")
        false_c = r.resolve("falseBranchColor")
        uncond_c = r.resolve("unconditionalBranchColor")

        mid1 = ay + ah + _FG_ROW_GAP // 2
        mid2 = by + bh + _FG_ROW_GAP // 2
        center = bx + bw // 2
        off = bw // 24  # true/false leave close to center
        self._edge(painter, uncond_c, [
            (ax + aw // 2, ay + ah), (ax + aw // 2, mid1),
            (center, mid1), (center, by)])
        self._edge(painter, true_c, [
            (center - off, by + bh), (center - off, mid2),
            (cx + cw // 2, mid2), (cx + cw // 2, cy)])
        self._edge(painter, false_c, [
            (center + off, by + bh), (center + off, mid2),
            (dx + dw // 2, mid2), (dx + dw // 2, cy)])
        # Back edge: same branch color (unconditional), 2x wide, routed up a narrow
        # lane into the top-left of the header (clear of the centered incoming edge).
        lane = cx - _FG_BACK_LANE
        b_top = bx + bw // 4
        self._edge(painter, uncond_c, [
            (cx, cy + ch // 2), (lane, cy + ch // 2),
            (lane, by - 10), (b_top, by - 10), (b_top, by)], width=2)

        self._draw_node(painter, r, ax, ay, aw, ah, _FG_NODE_A)
        self._draw_node(painter, r, bx, by, bw, bh, _FG_NODE_B)
        self._draw_node(painter, r, cx, cy, cw, ch, _FG_NODE_C)
        self._draw_node(painter, r, dx, cy, dw, dh, _FG_NODE_D)

    def _draw_node(self, painter, r, nx, ny, nw, nh, lines):
        grad = QLinearGradient(nx, ny, nx, ny + nh)
        grad.setColorAt(0.0, r.resolve("graphNodeLightColor"))
        grad.setColorAt(1.0, r.resolve("graphNodeDarkColor"))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(r.resolve("graphNodeOutlineColor"), 1))
        painter.drawRect(nx, ny, nw, nh)

        painter.save()
        painter.setClipRect(QRect(nx, ny, nw, nh))
        ascent = self._metrics.ascent()
        ty = ny + _NODE_PAD
        for line in lines:
            self._draw_tokens(painter, r, line, nx + _NODE_PAD, ty + ascent)
            ty += self._metrics.height()
        painter.restore()

    def _edge(self, painter, color, points, width=1):
        painter.setPen(QPen(color, width))
        painter.setBrush(QBrush(color))
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        self._arrowhead(painter, points[-2], points[-1])

    def _arrowhead(self, painter, frm, to):
        x1, y1 = frm
        x2, y2 = to
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / length, dy / length
        bx, by = x2 - ux * 9, y2 - uy * 9
        px, py = -uy * 5, ux * 5
        painter.drawPolygon([
            QPointF(x2, y2),
            QPointF(bx + px, by + py),
            QPointF(bx - px, by - py),
        ])
