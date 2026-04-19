"""
MicroPython I2C Driver for 128x128 OLED Display (SSD1327)
==========================================================
Compatible with: SSD1327-based 128x128 grayscale OLED displays
I2C default address: 0x3C (or 0x3D if SA0 pin is HIGH)

Usage Example:
    from machine import I2C, Pin
    from ssd1327 import SSD1327

    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    oled = SSD1327(i2c)

    oled.fill(0)
    oled.text("Hello!", 0, 0, 15)
    oled.show()
"""

import framebuf
from micropython import const

# ── SSD1327 Command Constants ──────────────────────────────────────────────────

_SET_COL_ADDR        = const(0x15)
_SET_ROW_ADDR        = const(0x75)
_SET_CONTRAST        = const(0x81)
_SET_REMAP           = const(0xA0)
_SET_DISPLAY_START   = const(0xA1)
_SET_DISPLAY_OFFSET  = const(0xA2)
_SET_DISPLAY_NORMAL  = const(0xA4)
_SET_DISPLAY_ALL_ON  = const(0xA5)
_SET_DISPLAY_ALL_OFF = const(0xA6)
_SET_DISPLAY_INVERT  = const(0xA7)
_SET_MUX_RATIO       = const(0xA8)
_SET_FUNC_SELECT_A   = const(0xAB)
_DISPLAY_OFF         = const(0xAE)
_DISPLAY_ON          = const(0xAF)
_SET_PHASE_LEN       = const(0xB1)
_SET_FRONT_CLK_DIV   = const(0xB3)
_SET_GPIO            = const(0xB5)
_SET_SECOND_PRECHARGE= const(0xB6)
_SET_GRAY_TABLE      = const(0xB8)
_SET_PRECHARGE_VOL   = const(0xBC)
_SET_VCOMH           = const(0xBE)
_SET_FUNC_SELECT_B   = const(0xD5)
_SET_COMMAND_LOCK    = const(0xFD)

_I2C_CMD_MODE        = const(0x00)   # Co=0, D/C#=0  → command stream
_I2C_DATA_MODE       = const(0x40)   # Co=0, D/C#=1  → data stream

WIDTH  = const(128)
HEIGHT = const(128)


class SSD1327(framebuf.FrameBuffer):
    """
    Driver for SSD1327-based 128×128 4-bit grayscale OLED.

    Inherits from FrameBuffer (GS4_HMSB format) so all standard
    FrameBuffer drawing primitives (pixel, line, rect, fill_rect,
    text, blit, …) are available.

    Grayscale levels: 0 (off) – 15 (full brightness).
    """

    def __init__(self, i2c, addr=0x3C, contrast=0x7F,
                 width=WIDTH, height=HEIGHT):
        self.i2c      = i2c
        self.addr     = addr
        self.width    = width
        self.height   = height
        # GS4_HMSB: 4 bits per pixel, high nibble first → width/2 bytes per row
        self._buf     = bytearray(width * height // 2)
        super().__init__(self._buf, width, height, framebuf.GS4_HMSB)
        self._init_display(contrast)

    # ── Low-level I2C helpers ─────────────────────────────────────────────────

    def _write_cmd(self, *cmds):
        """Send one or more command bytes."""
        for cmd in cmds:
            self.i2c.writeto(self.addr, bytes([_I2C_CMD_MODE, cmd]))

    def _write_data(self, data):
        """Send a data buffer preceded by the data control byte."""
        # Prepend the data-mode control byte
        buf = bytearray(len(data) + 1)
        buf[0] = _I2C_DATA_MODE
        buf[1:] = data
        self.i2c.writeto(self.addr, buf)

    # ── Initialisation sequence ───────────────────────────────────────────────

    def _init_display(self, contrast):
        cmds = (
            _DISPLAY_OFF,
            _SET_COMMAND_LOCK,    0x12,          # Unlock
            _SET_MUX_RATIO,       0x7F,          # 1/128 duty
            _SET_DISPLAY_OFFSET,  0x00,
            _SET_DISPLAY_START,   0x00,
            _SET_REMAP,           0x51,          # Enable COM split, col remap
            _SET_FRONT_CLK_DIV,   0x01,          # Divide ratio=1, Fosc=0
            _SET_PHASE_LEN,       0x51,          # Phase 1=1, Phase 2=5
            _SET_GPIO,            0x02,          # GPIO1 = output low
            _SET_FUNC_SELECT_A,   0x01,          # Enable internal VDD regulator
            _SET_PRECHARGE_VOL,   0x08,
            _SET_VCOMH,           0x07,
            _SET_CONTRAST,        contrast,
            _SET_SECOND_PRECHARGE,0x01,
            _SET_FUNC_SELECT_B,   0x62,          # Enable second precharge
            _SET_DISPLAY_NORMAL,
            _DISPLAY_ON,
        )
        for cmd in cmds:
            self._write_cmd(cmd)

    # ── Public API ────────────────────────────────────────────────────────────

    def show(self):
        """Push the FrameBuffer contents to the display."""
        self._write_cmd(
            _SET_COL_ADDR, 0x00, 0x3F,   # columns 0-63  (each byte = 2 pixels)
            _SET_ROW_ADDR, 0x00, 0x7F,   # rows    0-127
        )
        self._write_data(self._buf)

    def contrast(self, level):
        """Set display contrast (0–255)."""
        self._write_cmd(_SET_CONTRAST, level & 0xFF)

    def invert(self, invert: bool):
        """Invert display pixels."""
        self._write_cmd(_SET_DISPLAY_INVERT if invert else _SET_DISPLAY_NORMAL)

    def poweroff(self):
        """Turn the display off (sleep mode)."""
        self._write_cmd(_DISPLAY_OFF)

    def poweron(self):
        """Wake the display from sleep mode."""
        self._write_cmd(_DISPLAY_ON)

    def fill(self, color):
        """Fill entire display with *color* (0–15)."""
        super().fill(color)

    # ── Convenience drawing helpers ───────────────────────────────────────────

    def draw_bitmap(self, x, y, bitmap, w, h, color=15, bg=0):
        """
        Draw a 1-bit monochrome *bitmap* (bytes/bytearray, row-major,
        MSB first) at (x, y) with foreground *color* and background *bg*.

        bitmap : flat bytes/bytearray, ceil(w/8) bytes per row.
        """
        bytes_per_row = (w + 7) // 8
        for row in range(h):
            for col in range(w):
                byte_idx = row * bytes_per_row + col // 8
                bit = (bitmap[byte_idx] >> (7 - col % 8)) & 1
                self.pixel(x + col, y + row, color if bit else bg)

    def hline_gray(self, x, y, w, color):
        """Horizontal line with grayscale *color* (0–15)."""
        self.hline(x, y, w, color)

    def vline_gray(self, x, y, h, color):
        """Vertical line with grayscale *color* (0–15)."""
        self.vline(x, y, h, color)

    def rect_outline(self, x, y, w, h, color):
        """Draw a hollow rectangle."""
        self.rect(x, y, w, h, color)

    def circle(self, cx, cy, r, color):
        """Draw a hollow circle using midpoint algorithm."""
        x, y, err = r, 0, 0
        while x >= y:
            for sx, sy in ((cx+x, cy+y), (cx-x, cy+y), (cx+x, cy-y),
                           (cx-x, cy-y), (cx+y, cy+x), (cx-y, cy+x),
                           (cx+y, cy-x), (cx-y, cy-x)):
                self.pixel(sx, sy, color)
            y += 1
            err += 2*y + 1
            if 2*(err - x) + 1 > 0:
                x -= 1
                err += 1 - 2*x

    def fill_circle(self, cx, cy, r, color):
        """Draw a filled circle."""
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.hline(cx - dx, cy + dy, 2 * dx + 1, color)

    def gradient_fill(self, x, y, w, h, c_start, c_end):
        """
        Fill a rectangle with a vertical gradient from *c_start* to *c_end*
        (both 0–15).
        """
        for row in range(h):
            t = row / max(h - 1, 1)
            color = int(c_start + (c_end - c_start) * t + 0.5)
            self.hline(x, y + row, w, max(0, min(15, color)))



