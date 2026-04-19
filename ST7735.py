"""
MicroPython driver for Adafruit ST7735 TFT display (1.8" 128x160, or 1.44" 128x128)
Supports SPI interface. Works on RP2040, ESP32, ESP8266, STM32, etc.

Wiring (typical):
  ST7735 VCC  -> 3.3V
  ST7735 GND  -> GND
  ST7735 SCK  -> SPI CLK (e.g. GP2 on Pico)
  ST7735 SDA  -> SPI MOSI (e.g. GP3 on Pico)
  ST7735 RES  -> GPIO (reset pin)
  ST7735 DC   -> GPIO (data/command pin)
  ST7735 CS   -> SPI CS / GPIO
  ST7735 BL   -> 3.3V or GPIO (backlight)

Usage:
    from machine import SPI, Pin
    import st7735

    spi = SPI(0, baudrate=20_000_000, polarity=0, phase=0,
              sck=Pin(2), mosi=Pin(3))
    display = st7735.ST7735(spi, cs=Pin(5), dc=Pin(6), rst=Pin(7),
                            width=128, height=160)
    display.fill(st7735.BLACK)
    display.text("Hello!", 10, 10, st7735.WHITE)
"""

from machine import Pin
import time
import struct

# ── Colour helpers (RGB565) ───────────────────────────────────────────────────
def color565(r, g, b):
    """Convert 8-bit R,G,B to packed 16-bit RGB565."""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

BLACK   = color565(0,   0,   0)
WHITE   = color565(255, 255, 255)
RED     = color565(255, 0,   0)
GREEN   = color565(0,   255, 0)
BLUE    = color565(0,   0,   255)
CYAN    = color565(0,   255, 255)
MAGENTA = color565(255, 0,   255)
YELLOW  = color565(255, 255, 0)
ORANGE  = color565(255, 165, 0)

# ── ST7735 command constants ──────────────────────────────────────────────────
_NOP        = 0x00
_SWRESET    = 0x01
_SLPOUT     = 0x11
_NORON      = 0x13
_INVOFF     = 0x20
_INVON      = 0x21
_DISPOFF    = 0x28
_DISPON     = 0x29
_CASET      = 0x2A
_RASET      = 0x2B
_RAMWR      = 0x2C
_MADCTL     = 0x36
_COLMOD     = 0x3A
_FRMCTR1    = 0xB1
_FRMCTR2    = 0xB2
_FRMCTR3    = 0xB3
_INVCTR     = 0xB4
_PWCTR1     = 0xC0
_PWCTR2     = 0xC1
_PWCTR3     = 0xC2
_PWCTR4     = 0xC3
_PWCTR5     = 0xC4
_VMCTR1     = 0xC5
_GMCTRP1    = 0xE0
_GMCTRN1    = 0xE1

# MADCTL rotation flags
_MADCTL_MY  = 0x80
_MADCTL_MX  = 0x40
_MADCTL_MV  = 0x20
_MADCTL_ML  = 0x10
_MADCTL_RGB = 0x00
_MADCTL_BGR = 0x08

# ── Built-in 5×8 font (ASCII 32-126) ─────────────────────────────────────────
# Each character is 5 columns of 8 bits (LSB = top row).
_FONT5X8 = (
    b'\x00\x00\x00\x00\x00'  # 32 space
    b'\x00\x00\x5F\x00\x00'  # 33 !
    b'\x00\x07\x00\x07\x00'  # 34 "
    b'\x14\x7F\x14\x7F\x14'  # 35 #
    b'\x24\x2A\x7F\x2A\x12'  # 36 $
    b'\x23\x13\x08\x64\x62'  # 37 %
    b'\x36\x49\x55\x22\x50'  # 38 &
    b'\x00\x05\x03\x00\x00'  # 39 '
    b'\x00\x1C\x22\x41\x00'  # 40 (
    b'\x00\x41\x22\x1C\x00'  # 41 )
    b'\x08\x2A\x1C\x2A\x08'  # 42 *
    b'\x08\x08\x3E\x08\x08'  # 43 +
    b'\x00\x50\x30\x00\x00'  # 44 ,
    b'\x08\x08\x08\x08\x08'  # 45 -
    b'\x00\x60\x60\x00\x00'  # 46 .
    b'\x20\x10\x08\x04\x02'  # 47 /
    b'\x3E\x51\x49\x45\x3E'  # 48 0
    b'\x00\x42\x7F\x40\x00'  # 49 1
    b'\x42\x61\x51\x49\x46'  # 50 2
    b'\x21\x41\x45\x4B\x31'  # 51 3
    b'\x18\x14\x12\x7F\x10'  # 52 4
    b'\x27\x45\x45\x45\x39'  # 53 5
    b'\x3C\x4A\x49\x49\x30'  # 54 6
    b'\x01\x71\x09\x05\x03'  # 55 7
    b'\x36\x49\x49\x49\x36'  # 56 8
    b'\x06\x49\x49\x29\x1E'  # 57 9
    b'\x00\x36\x36\x00\x00'  # 58 :
    b'\x00\x56\x36\x00\x00'  # 59 ;
    b'\x00\x08\x14\x22\x41'  # 60 <
    b'\x14\x14\x14\x14\x14'  # 61 =
    b'\x41\x22\x14\x08\x00'  # 62 >
    b'\x02\x01\x51\x09\x06'  # 63 ?
    b'\x32\x49\x79\x41\x3E'  # 64 @
    b'\x7E\x11\x11\x11\x7E'  # 65 A
    b'\x7F\x49\x49\x49\x36'  # 66 B
    b'\x3E\x41\x41\x41\x22'  # 67 C
    b'\x7F\x41\x41\x22\x1C'  # 68 D
    b'\x7F\x49\x49\x49\x41'  # 69 E
    b'\x7F\x09\x09\x01\x01'  # 70 F
    b'\x3E\x41\x41\x51\x32'  # 71 G
    b'\x7F\x08\x08\x08\x7F'  # 72 H
    b'\x00\x41\x7F\x41\x00'  # 73 I
    b'\x20\x40\x41\x3F\x01'  # 74 J
    b'\x7F\x08\x14\x22\x41'  # 75 K
    b'\x7F\x40\x40\x40\x40'  # 76 L
    b'\x7F\x02\x04\x02\x7F'  # 77 M
    b'\x7F\x04\x08\x10\x7F'  # 78 N
    b'\x3E\x41\x41\x41\x3E'  # 79 O
    b'\x7F\x09\x09\x09\x06'  # 80 P
    b'\x3E\x41\x51\x21\x5E'  # 81 Q
    b'\x7F\x09\x19\x29\x46'  # 82 R
    b'\x46\x49\x49\x49\x31'  # 83 S
    b'\x01\x01\x7F\x01\x01'  # 84 T
    b'\x3F\x40\x40\x40\x3F'  # 85 U
    b'\x1F\x20\x40\x20\x1F'  # 86 V
    b'\x7F\x20\x18\x20\x7F'  # 87 W
    b'\x63\x14\x08\x14\x63'  # 88 X
    b'\x03\x04\x78\x04\x03'  # 89 Y
    b'\x61\x51\x49\x45\x43'  # 90 Z
    b'\x00\x00\x7F\x41\x41'  # 91 [
    b'\x02\x04\x08\x10\x20'  # 92 backslash
    b'\x41\x41\x7F\x00\x00'  # 93 ]
    b'\x04\x02\x01\x02\x04'  # 94 ^
    b'\x40\x40\x40\x40\x40'  # 95 _
    b'\x00\x01\x02\x04\x00'  # 96 `
    b'\x20\x54\x54\x54\x78'  # 97 a
    b'\x7F\x48\x44\x44\x38'  # 98 b
    b'\x38\x44\x44\x44\x20'  # 99 c
    b'\x38\x44\x44\x48\x7F'  # 100 d
    b'\x38\x54\x54\x54\x18'  # 101 e
    b'\x08\x7E\x09\x01\x02'  # 102 f
    b'\x08\x14\x54\x54\x3C'  # 103 g
    b'\x7F\x08\x04\x04\x78'  # 104 h
    b'\x00\x44\x7D\x40\x00'  # 105 i
    b'\x20\x40\x44\x3D\x00'  # 106 j
    b'\x00\x7F\x10\x28\x44'  # 107 k
    b'\x00\x41\x7F\x40\x00'  # 108 l
    b'\x7C\x04\x18\x04\x78'  # 109 m
    b'\x7C\x08\x04\x04\x78'  # 110 n
    b'\x38\x44\x44\x44\x38'  # 111 o
    b'\x7C\x14\x14\x14\x08'  # 112 p
    b'\x08\x14\x14\x18\x7C'  # 113 q
    b'\x7C\x08\x04\x04\x08'  # 114 r
    b'\x48\x54\x54\x54\x20'  # 115 s
    b'\x04\x3F\x44\x40\x20'  # 116 t
    b'\x3C\x40\x40\x20\x7C'  # 117 u
    b'\x1C\x20\x40\x20\x1C'  # 118 v
    b'\x3C\x40\x30\x40\x3C'  # 119 w
    b'\x44\x28\x10\x28\x44'  # 120 x
    b'\x0C\x50\x50\x50\x3C'  # 121 y
    b'\x44\x64\x54\x4C\x44'  # 122 z
    b'\x00\x08\x36\x41\x00'  # 123 {
    b'\x00\x00\x7F\x00\x00'  # 124 |
    b'\x00\x41\x36\x08\x00'  # 125 }
    b'\x08\x08\x2A\x1C\x08'  # 126 ~
)


class ST7735:
    """
    Driver for the Sitronix ST7735 TFT LCD controller.

    Parameters
    ----------
    spi       : machine.SPI instance (configured by caller)
    cs        : chip-select Pin
    dc        : data/command Pin
    rst       : reset Pin (optional, pass None to skip HW reset)
    width     : display width  in pixels  (default 128)
    height    : display height in pixels  (default 160)
    rotation  : 0, 90, 180, or 270        (default 0)
    bgr       : True if display uses BGR order (most Adafruit boards = False)
    offset_x  : column offset  (1.44" 128×128 needs x=2, y=3 typically)
    offset_y  : row offset
    """

    def __init__(self, spi, cs, dc, rst=None,
                 width=128, height=160,
                 rotation=0, bgr=False,
                 offset_x=0, offset_y=0):
        self.spi = spi
        self.cs  = cs
        self.dc  = dc
        self.rst = rst
        self.width    = width
        self.height   = height
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._bgr = bgr

        self.cs.init(Pin.OUT, value=1)
        self.dc.init(Pin.OUT, value=0)
        if self.rst:
            self.rst.init(Pin.OUT, value=1)

        self._reset()
        self._init_display()
        self.set_rotation(rotation)

    # ── Low-level SPI helpers ─────────────────────────────────────────────────

    def _reset(self):
        if self.rst:
            self.rst(1); time.sleep_ms(10)
            self.rst(0); time.sleep_ms(50)
            self.rst(1); time.sleep_ms(150)

    def _write_cmd(self, cmd):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytes([cmd]))
        self.cs(1)

    def _write_data(self, data):
        self.dc(1)
        self.cs(0)
        self.spi.write(data)
        self.cs(1)

    def _write_cmd_data(self, cmd, *args):
        self._write_cmd(cmd)
        if args:
            self._write_data(bytes(args))

    # ── Initialisation sequence ───────────────────────────────────────────────

    def _init_display(self):
        cmds = [
            (_SWRESET, None,  150),   # software reset
            (_SLPOUT,  None,  500),   # sleep out
            (_FRMCTR1, b'\x01\x2C\x2D', 0),
            (_FRMCTR2, b'\x01\x2C\x2D', 0),
            (_FRMCTR3, b'\x01\x2C\x2D\x01\x2C\x2D', 0),
            (_INVCTR,  b'\x07', 0),
            (_PWCTR1,  b'\xA2\x02\x84', 0),
            (_PWCTR2,  b'\xC5', 0),
            (_PWCTR3,  b'\x0A\x00', 0),
            (_PWCTR4,  b'\x8A\x2A', 0),
            (_PWCTR5,  b'\x8A\xEE', 0),
            (_VMCTR1,  b'\x0E', 0),
            (_INVOFF,  None,  0),
            # Positive gamma
            (_GMCTRP1, b'\x02\x1C\x07\x12\x37\x32\x29\x2D'
                        b'\x29\x25\x2B\x39\x00\x01\x03\x10', 0),
            # Negative gamma
            (_GMCTRN1, b'\x03\x1D\x07\x06\x2E\x2C\x29\x2D'
                        b'\x2E\x2E\x37\x3F\x00\x00\x02\x10', 0),
            (_COLMOD,  b'\x05', 10),  # 16-bit colour
            (_NORON,   None,   10),
            (_DISPON,  None,  100),
        ]
        for cmd, data, delay in cmds:
            self._write_cmd(cmd)
            if data:
                self._write_data(data)
            if delay:
                time.sleep_ms(delay)

    # ── Rotation / MADCTL ─────────────────────────────────────────────────────

    def set_rotation(self, rotation):
        """Set display rotation: 0, 90, 180, or 270 degrees."""
        rotation = rotation % 360
        bgr = _MADCTL_BGR if self._bgr else _MADCTL_RGB
        if rotation == 0:
            madctl = _MADCTL_MX | _MADCTL_MY | bgr
            self._width, self._height = self.width, self.height
        elif rotation == 90:
            madctl = _MADCTL_MY | _MADCTL_MV | bgr
            self._width, self._height = self.height, self.width
        elif rotation == 180:
            madctl = bgr
            self._width, self._height = self.width, self.height
        else:  # 270
            madctl = _MADCTL_MX | _MADCTL_MV | bgr
            self._width, self._height = self.height, self.width
        self._write_cmd_data(_MADCTL, madctl)

    # ── Address window ────────────────────────────────────────────────────────

    def _set_window(self, x0, y0, x1, y1):
        x0 += self._offset_x; x1 += self._offset_x
        y0 += self._offset_y; y1 += self._offset_y
        self._write_cmd(_CASET)
        self._write_data(struct.pack('>HH', x0, x1))
        self._write_cmd(_RASET)
        self._write_data(struct.pack('>HH', y0, y1))
        self._write_cmd(_RAMWR)

    # ── Drawing primitives ────────────────────────────────────────────────────

    def fill(self, color):
        """Fill the entire screen with a colour."""
        self.fill_rect(0, 0, self._width, self._height, color)

    def fill_rect(self, x, y, w, h, color):
        """Draw a filled rectangle."""
        if x >= self._width or y >= self._height or w <= 0 or h <= 0:
            return
        x = max(0, x); y = max(0, y)
        w = min(w, self._width  - x)
        h = min(h, self._height - y)
        self._set_window(x, y, x + w - 1, y + h - 1)
        hi, lo = color >> 8, color & 0xFF
        chunk = bytes([hi, lo] * 32)          # 32 pixels per chunk
        pixels = w * h
        self.dc(1); self.cs(0)
        full, rem = divmod(pixels, 32)
        for _ in range(full):
            self.spi.write(chunk)
        if rem:
            self.spi.write(bytes([hi, lo] * rem))
        self.cs(1)

    def pixel(self, x, y, color):
        """Draw a single pixel."""
        if 0 <= x < self._width and 0 <= y < self._height:
            self._set_window(x, y, x, y)
            self._write_data(struct.pack('>H', color))

    def hline(self, x, y, w, color):
        """Draw a horizontal line."""
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        """Draw a vertical line."""
        self.fill_rect(x, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color):
        """Draw a line using Bresenham's algorithm."""
        dx = abs(x1 - x0); dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = err * 2
            if e2 > -dy:
                err -= dy; x0 += sx
            if e2 < dx:
                err += dx; y0 += sy

    def rect(self, x, y, w, h, color):
        """Draw a hollow rectangle."""
        self.hline(x,         y,         w, color)
        self.hline(x,         y + h - 1, w, color)
        self.vline(x,         y,         h, color)
        self.vline(x + w - 1, y,         h, color)

    def circle(self, cx, cy, r, color):
        """Draw a hollow circle (Midpoint algorithm)."""
        x, y, err = 0, r, 3 - 2 * r
        while x <= y:
            for dx, dy in ((x,y),(y,x),(-x,y),(-y,x),(x,-y),(y,-x),(-x,-y),(-y,-x)):
                self.pixel(cx + dx, cy + dy, color)
            x += 1
            err += (4*x - 2) if err > 0 else (4*(x - y) + 10)
            if err > 0:
                y -= 1

    def fill_circle(self, cx, cy, r, color):
        """Draw a filled circle."""
        x, y, err = 0, r, 3 - 2 * r
        while x <= y:
            self.hline(cx - y, cy + x, 2*y + 1, color)
            self.hline(cx - y, cy - x, 2*y + 1, color)
            self.hline(cx - x, cy + y, 2*x + 1, color)
            self.hline(cx - x, cy - y, 2*x + 1, color)
            x += 1
            err += (4*x - 2) if err > 0 else (4*(x - y) + 10)
            if err > 0:
                y -= 1

    # ── Text rendering (built-in 5×8 font) ───────────────────────────────────

    def _char(self, x, y, ch, fg, bg, scale=1):
        code = ord(ch)
        if code < 32 or code > 126:
            code = 32
        idx = (code - 32) * 5
        glyph = _FONT5X8[idx:idx + 5]
        for col, bits in enumerate(glyph):
            for row in range(8):
                px = x + col * scale
                py = y + row * scale
                c = fg if (bits >> row) & 1 else bg
                if scale == 1:
                    self.pixel(px, py, c)
                else:
                    self.fill_rect(px, py, scale, scale, c)
        # one-pixel gap column
        if bg is not None:
            gap_x = x + 5 * scale
            for row in range(8 * scale):
                if scale == 1:
                    self.pixel(gap_x, y + row, bg)
                else:
                    self.fill_rect(gap_x, y + row, scale, scale, bg)

    def text(self, string, x, y, fg=WHITE, bg=BLACK, scale=1):
        """
        Draw a string using the built-in 5×8 pixel font.

        Parameters
        ----------
        string : text to display
        x, y   : top-left origin
        fg     : foreground colour (RGB565)
        bg     : background colour (RGB565), or None for transparent bg
        scale  : integer magnification factor (1 = normal, 2 = double, …)
        """
        cx = x
        char_w = (5 + 1) * scale
        for ch in string:
            if ch == '\n':
                y += 8 * scale; cx = x
            elif ch == '\r':
                cx = x
            else:
                if cx + char_w > self._width:
                    y += 8 * scale; cx = x
                self._char(cx, y, ch, fg, bg, scale)
                cx += char_w

    # ── Bitmap / raw framebuffer ──────────────────────────────────────────────

    def blit_buffer(self, buf, x, y, w, h):
        """
        Write a raw RGB565 byte buffer to the display.

        ``buf`` must be a bytes-like object of length w * h * 2.
        """
        self._set_window(x, y, x + w - 1, y + h - 1)
        self._write_data(buf)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def invert(self, enable=True):
        """Invert the display colours."""
        self._write_cmd(_INVON if enable else _INVOFF)

    def on(self):
        """Turn display on."""
        self._write_cmd(_DISPON)

    def off(self):
        """Turn display off (backlight stays on)."""
        self._write_cmd(_DISPOFF)

    @property
    def size(self):
        """Return current (width, height) accounting for rotation."""
        return self._width, self._height
