"""
MicroPython I2C Driver for SH1107 128x128 OLED Display
=======================================================
Compatible with: SH1107-based 128x128 monochrome OLED displays
I2C default address: 0x3C (or 0x3D if SA0/DC pin is HIGH)

Supported rotations: 0 / 90 / 180 / 270

Image display
-------------
Use the companion convert_image.py script (on your PC) to convert any
PNG/JPG/BMP/etc. to a .img file, then call:

    oled.draw_image("photo.img", x, y, w, h)

The image will be scaled to fit the (w x h) rectangle with the top-left
corner at (x, y).  The .img format is a tiny binary:
  bytes 0-1  : uint16 big-endian  width
  bytes 2-3  : uint16 big-endian  height
  bytes 4..  : 1-bit pixels, MSB first, row-major, ceil(w/8) bytes per row

Usage Example:
    from machine import I2C, Pin
    from sh1107 import SH1107

    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400_000)
    oled = SH1107(i2c, rotation=90)

    oled.fill(0)
    oled.draw_image("logo.img", 0, 0, 128, 64)   # scale to 128x64
    oled.text("Hello!", 0, 68, 1)
    oled.show()
"""

import framebuf
import struct
from micropython import const

# ── SH1107 Commands ────────────────────────────────────────────────────────────

_SET_LOW_COL               = const(0x00)
_SET_HIGH_COL              = const(0x10)
_SET_CONTRAST              = const(0x81)
_SET_SEG_REMAP_OFF         = const(0xA0)
_SET_SEG_REMAP_ON          = const(0xA1)
_SET_DISPLAY_NORMAL        = const(0xA4)
_SET_DISPLAY_NORMAL_PIXELS = const(0xA6)
_SET_DISPLAY_INVERT_PIXELS = const(0xA7)
_SET_MUX_RATIO             = const(0xA8)
_SET_DCDC                  = const(0xAD)
_DISPLAY_OFF               = const(0xAE)
_DISPLAY_ON                = const(0xAF)
_SET_PAGE_ADDR             = const(0xB0)
_SET_COM_SCAN_INC          = const(0xC0)
_SET_COM_SCAN_DEC          = const(0xC8)
_SET_DISPLAY_OFFSET        = const(0xD3)
_SET_CLK_DIV               = const(0xD5)
_SET_PRECHARGE             = const(0xD9)
_SET_COM_PINS              = const(0xDA)
_SET_VCOMH                 = const(0xDB)
_SET_DISPLAY_START         = const(0xDC)

_I2C_CMD_MODE  = const(0x00)
_I2C_DATA_MODE = const(0x40)

WIDTH  = const(128)
HEIGHT = const(128)
PAGES  = const(16)


class SH1107(framebuf.FrameBuffer):
    """
    Driver for SH1107-based 128x128 monochrome OLED.

    rotation : 0 | 90 | 180 | 270
      0 / 180  -> hardware remap, no CPU cost in show()
      90 / 270 -> software pixel transpose in show()

    Pixel colour: 0 = off, 1 = on.
    """

    def __init__(self, i2c, addr=0x3C, contrast=0x7F,
                 width=WIDTH, height=HEIGHT, rotation=0):
        if rotation not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180 or 270")

        self.i2c       = i2c
        self.addr      = addr
        self.width     = width
        self.height    = height
        self._rotation = rotation

        self._buf = bytearray(width * height // 8)
        super().__init__(self._buf, width, height, framebuf.MONO_VLSB)
        self._init_display(contrast, rotation)

    # ── Low-level I2C ─────────────────────────────────────────────────────────

    def _cmd(self, *cmds):
        for c in cmds:
            self.i2c.writeto(self.addr, bytes([_I2C_CMD_MODE, c]))

    def _data(self, buf):
        tmp = bytearray(len(buf) + 1)
        tmp[0] = _I2C_DATA_MODE
        tmp[1:] = buf
        self.i2c.writeto(self.addr, tmp)

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_display(self, contrast, rotation):
        self._cmd(_DISPLAY_OFF)
        self._cmd(_SET_CLK_DIV,        0x51)
        self._cmd(_SET_MUX_RATIO,      0x7F)
        self._cmd(_SET_DISPLAY_START,  0x00)
        self._cmd(_SET_DISPLAY_OFFSET, 0x00)
        self._cmd(_SET_COM_PINS,       0x12)
        self._cmd(_SET_CONTRAST,       contrast)
        self._cmd(_SET_PRECHARGE,      0x22)
        self._cmd(_SET_VCOMH,          0x35)
        self._cmd(_SET_DCDC,           0x8B)
        self._cmd(_SET_DISPLAY_NORMAL_PIXELS)
        self._cmd(_SET_DISPLAY_NORMAL)
        self._apply_hw_remap(rotation)
        self._cmd(_DISPLAY_ON)

    def _apply_hw_remap(self, rotation):
        if rotation == 180:
            self._cmd(_SET_SEG_REMAP_OFF)
            self._cmd(_SET_COM_SCAN_INC)
        else:
            self._cmd(_SET_SEG_REMAP_ON)
            self._cmd(_SET_COM_SCAN_DEC)

    # ── show() ────────────────────────────────────────────────────────────────

    def show(self):
        if self._rotation in (0, 180):
            self._show_direct()
        elif self._rotation == 90:
            self._show_transposed_90()
        else:
            self._show_transposed_270()

    def _show_direct(self):
        for page in range(PAGES):
            self._cmd(
                _SET_PAGE_ADDR | page,
                _SET_LOW_COL   | 0x00,
                _SET_HIGH_COL  | 0x00,
            )
            self._data(self._buf[page * WIDTH : page * WIDTH + WIDTH])

    def _show_transposed_90(self):
        # 90 CW: lx = phys_row,  ly = HEIGHT-1-phys_col
        out = bytearray(WIDTH * HEIGHT // 8)
        for page in range(PAGES):
            base = page * 8
            for phys_col in range(WIDTH):
                byte_val = 0
                for bit in range(8):
                    phys_row = base + bit
                    lx = phys_row
                    ly = HEIGHT - 1 - phys_col
                    if 0 <= lx < WIDTH and 0 <= ly < HEIGHT:
                        p = (self._buf[(ly >> 3) * WIDTH + lx] >> (ly & 7)) & 1
                    else:
                        p = 0
                    byte_val |= p << bit
                out[page * WIDTH + phys_col] = byte_val
        for page in range(PAGES):
            self._cmd(_SET_PAGE_ADDR | page, _SET_LOW_COL | 0, _SET_HIGH_COL | 0)
            self._data(out[page * WIDTH : page * WIDTH + WIDTH])

    def _show_transposed_270(self):
        # 270 CW: lx = WIDTH-1-phys_row,  ly = phys_col
        out = bytearray(WIDTH * HEIGHT // 8)
        for page in range(PAGES):
            base = page * 8
            for phys_col in range(WIDTH):
                byte_val = 0
                for bit in range(8):
                    phys_row = base + bit
                    lx = WIDTH - 1 - phys_row
                    ly = phys_col
                    if 0 <= lx < WIDTH and 0 <= ly < HEIGHT:
                        p = (self._buf[(ly >> 3) * WIDTH + lx] >> (ly & 7)) & 1
                    else:
                        p = 0
                    byte_val |= p << bit
                out[page * WIDTH + phys_col] = byte_val
        for page in range(PAGES):
            self._cmd(_SET_PAGE_ADDR | page, _SET_LOW_COL | 0, _SET_HIGH_COL | 0)
            self._data(out[page * WIDTH : page * WIDTH + WIDTH])

    # ── Public API ────────────────────────────────────────────────────────────

    def set_rotation(self, rotation):
        """Change rotation at runtime. Call show() to update the display."""
        if rotation not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180 or 270")
        self._rotation = rotation
        self._apply_hw_remap(rotation)

    def contrast(self, level):
        """Set contrast 0-255."""
        self._cmd(_SET_CONTRAST, level & 0xFF)

    def invert(self, invert):
        """Invert pixel polarity."""
        self._cmd(_SET_DISPLAY_INVERT_PIXELS if invert
                  else _SET_DISPLAY_NORMAL_PIXELS)

    def poweroff(self):
        self._cmd(_DISPLAY_OFF)

    def poweron(self):
        self._cmd(_DISPLAY_ON)

    # ── Image display ─────────────────────────────────────────────────────────

    def draw_image(self, filename, x, y, w, h, invert=False, threshold=128):
        """
        Draw a .img file into the rectangle (x, y, w, h).

        The image is scaled to fit (w x h) using nearest-neighbour resampling
        so that no floats or large buffers are needed on the microcontroller.

        Parameters
        ----------
        filename  : path to a .img file produced by convert_image.py
        x, y      : top-left corner on the display canvas
        w, h      : size of the destination rectangle (scales the image)
        invert    : flip black/white in the image (default False)
        threshold : ignored for pre-dithered .img files; reserved for raw use

        The .img binary format (produced by convert_image.py):
          bytes 0-1  uint16 big-endian  source width
          bytes 2-3  uint16 big-endian  source height
          bytes 4..  1-bit pixels, MSB first, row-major, ceil(w/8) bytes/row
        """
        with open(filename, "rb") as f:
            src_w, src_h = struct.unpack(">HH", f.read(4))
            bpr = (src_w + 7) // 8          # source bytes per row
            # Read entire pixel data into RAM.
            # Max size for 128x128 = 2048 bytes — fine on any MicroPython board.
            pixel_data = f.read(bpr * src_h)

        # Nearest-neighbour scale: iterate over destination pixels
        for dy in range(h):
            # Map destination row -> source row
            sy = (dy * src_h) // h
            row_offset = sy * bpr
            for dx in range(w):
                # Map destination col -> source col
                sx = (dx * src_w) // w
                # Read the bit from the packed source row
                src_byte = pixel_data[row_offset + (sx >> 3)]
                bit = (src_byte >> (7 - (sx & 7))) & 1
                if invert:
                    bit ^= 1
                self.pixel(x + dx, y + dy, bit)

    # ── Extra drawing helpers ─────────────────────────────────────────────────

    def circle(self, cx, cy, r, color=1):
        """Hollow circle via midpoint algorithm."""
        x, y, err = r, 0, 0
        while x >= y:
            for px, py in ((cx+x,cy+y),(cx-x,cy+y),(cx+x,cy-y),(cx-x,cy-y),
                           (cx+y,cy+x),(cx-y,cy+x),(cx+y,cy-x),(cx-y,cy-x)):
                self.pixel(px, py, color)
            y += 1; err += 2*y + 1
            if 2*(err - x) + 1 > 0:
                x -= 1; err += 1 - 2*x

    def fill_circle(self, cx, cy, r, color=1):
        """Filled circle."""
        for dy in range(-r, r + 1):
            dx = int((r*r - dy*dy) ** 0.5)
            self.hline(cx - dx, cy + dy, 2*dx + 1, color)
    def text_wrapped(self, string, x, y, color=1, max_chars=16, line_height=15, wrap_on_space=False):
        """
        Draw text with automatic line-wrapping.

        If the string exceeds max_chars characters, it is split across
        multiple lines, each offset downward by line_height pixels.

        When wrap_on_space=False (default): wraps only when a line would
        exceed max_chars, respecting word boundaries where possible.

        When wrap_on_space=True: wraps at every space character regardless
        of line length, stripping the space itself from the output.

        Long words that exceed max_chars on their own are always hard-broken.

        Parameters
        ----------
        string        : text to draw
        x, y          : top-left corner of the first line
        color         : pixel value (default 1 = on)
        max_chars     : character limit per line before wrapping (default 16)
        line_height   : vertical step in pixels between lines (default 15)
        wrap_on_space : if True, wrap at every space even if under max_chars
                        and strip the space from the output (default False)

        Example
        -------
            oled.text_wrapped("Hello, this is a long string!", 0, 0)
            oled.text_wrapped("Wrap at every space", 0, 0, wrap_on_space=True)
            oled.show()
        """
        if wrap_on_space:
            # Split on every space; each segment becomes its own line.
            # Still hard-break any segment longer than max_chars.
            segments = string.split(" ")
            lines = []
            for seg in segments:
                while len(seg) > max_chars:
                    lines.append(seg[:max_chars])
                    seg = seg[max_chars:]
                lines.append(seg)
        else:
            words = string.split(" ")
            lines = []
            current = ""

            for word in words:
                # Hard-break any word longer than max_chars
                while len(word) > max_chars:
                    space_left = max_chars - len(current) - (1 if current else 0)
                    if space_left > 0:
                        chunk = word[:space_left]
                        current = (current + " " + chunk) if current else chunk
                        word = word[space_left:]
                    lines.append(current)
                    current = ""

                # Normal word: try to fit on the current line
                candidate = (current + " " + word) if current else word
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word

            if current:
                lines.append(current)

        # Render each line
        for i, line in enumerate(lines):
            self.text(line, x, y + i * line_height, color)
    def draw_bitmap(self, x, y, bitmap, w, h, color=1, bg=0):
        """Render a 1-bit MSB-first row-major bitmap at (x, y)."""
        bpr = (w + 7) // 8
        for row in range(h):
            for col in range(w):
                bit = (bitmap[row*bpr + col//8] >> (7 - col%8)) & 1
                self.pixel(x+col, y+row, color if bit else bg)

    # ── Scaled text ───────────────────────────────────────────────────────────
    #
    # MicroPython's built-in font is 8x8 pixels per character.
    # Each character is encoded as 8 bytes, one byte per row, MSB = leftmost pixel.
    # The font data below is the standard MicroPython/SSD1306 bitmap font (ASCII 32-127).

    # fmt: off
    _FONT = (
        b'\x00\x00\x00\x00\x00\x00\x00\x00',  # 32  (space)
        b'\x00\x00\x5F\x00\x00\x00\x00\x00',  # 33  !
        b'\x00\x07\x00\x07\x00\x00\x00\x00',  # 34  "
        b'\x14\x7F\x14\x7F\x14\x00\x00\x00',  # 35  #
        b'\x24\x2A\x7F\x2A\x12\x00\x00\x00',  # 36  $
        b'\x23\x13\x08\x64\x62\x00\x00\x00',  # 37  %
        b'\x36\x49\x55\x22\x50\x00\x00\x00',  # 38  &
        b'\x00\x05\x03\x00\x00\x00\x00\x00',  # 39  '
        b'\x00\x1C\x22\x41\x00\x00\x00\x00',  # 40  (
        b'\x00\x41\x22\x1C\x00\x00\x00\x00',  # 41  )
        b'\x14\x08\x3E\x08\x14\x00\x00\x00',  # 42  *
        b'\x08\x08\x3E\x08\x08\x00\x00\x00',  # 43  +
        b'\x00\x50\x30\x00\x00\x00\x00\x00',  # 44  ,
        b'\x08\x08\x08\x08\x08\x00\x00\x00',  # 45  -
        b'\x00\x60\x60\x00\x00\x00\x00\x00',  # 46  .
        b'\x20\x10\x08\x04\x02\x00\x00\x00',  # 47  /
        b'\x3E\x51\x49\x45\x3E\x00\x00\x00',  # 48  0
        b'\x00\x42\x7F\x40\x00\x00\x00\x00',  # 49  1
        b'\x42\x61\x51\x49\x46\x00\x00\x00',  # 50  2
        b'\x21\x41\x45\x4B\x31\x00\x00\x00',  # 51  3
        b'\x18\x14\x12\x7F\x10\x00\x00\x00',  # 52  4
        b'\x27\x45\x45\x45\x39\x00\x00\x00',  # 53  5
        b'\x3C\x4A\x49\x49\x30\x00\x00\x00',  # 54  6
        b'\x01\x71\x09\x05\x03\x00\x00\x00',  # 55  7
        b'\x36\x49\x49\x49\x36\x00\x00\x00',  # 56  8
        b'\x06\x49\x49\x29\x1E\x00\x00\x00',  # 57  9
        b'\x00\x36\x36\x00\x00\x00\x00\x00',  # 58  :
        b'\x00\x56\x36\x00\x00\x00\x00\x00',  # 59  ;
        b'\x08\x14\x22\x41\x00\x00\x00\x00',  # 60  <
        b'\x14\x14\x14\x14\x14\x00\x00\x00',  # 61  =
        b'\x00\x41\x22\x14\x08\x00\x00\x00',  # 62  >
        b'\x02\x01\x51\x09\x06\x00\x00\x00',  # 63  ?
        b'\x32\x49\x79\x41\x3E\x00\x00\x00',  # 64  @
        b'\x7E\x11\x11\x11\x7E\x00\x00\x00',  # 65  A
        b'\x7F\x49\x49\x49\x36\x00\x00\x00',  # 66  B
        b'\x3E\x41\x41\x41\x22\x00\x00\x00',  # 67  C
        b'\x7F\x41\x41\x22\x1C\x00\x00\x00',  # 68  D
        b'\x7F\x49\x49\x49\x41\x00\x00\x00',  # 69  E
        b'\x7F\x09\x09\x09\x01\x00\x00\x00',  # 70  F
        b'\x3E\x41\x49\x49\x7A\x00\x00\x00',  # 71  G
        b'\x7F\x08\x08\x08\x7F\x00\x00\x00',  # 72  H
        b'\x00\x41\x7F\x41\x00\x00\x00\x00',  # 73  I
        b'\x20\x40\x41\x3F\x01\x00\x00\x00',  # 74  J
        b'\x7F\x08\x14\x22\x41\x00\x00\x00',  # 75  K
        b'\x7F\x40\x40\x40\x40\x00\x00\x00',  # 76  L
        b'\x7F\x02\x0C\x02\x7F\x00\x00\x00',  # 77  M
        b'\x7F\x04\x08\x10\x7F\x00\x00\x00',  # 78  N
        b'\x3E\x41\x41\x41\x3E\x00\x00\x00',  # 79  O
        b'\x7F\x09\x09\x09\x06\x00\x00\x00',  # 80  P
        b'\x3E\x41\x51\x21\x5E\x00\x00\x00',  # 81  Q
        b'\x7F\x09\x19\x29\x46\x00\x00\x00',  # 82  R
        b'\x46\x49\x49\x49\x31\x00\x00\x00',  # 83  S
        b'\x01\x01\x7F\x01\x01\x00\x00\x00',  # 84  T
        b'\x3F\x40\x40\x40\x3F\x00\x00\x00',  # 85  U
        b'\x1F\x20\x40\x20\x1F\x00\x00\x00',  # 86  V
        b'\x3F\x40\x38\x40\x3F\x00\x00\x00',  # 87  W
        b'\x63\x14\x08\x14\x63\x00\x00\x00',  # 88  X
        b'\x07\x08\x70\x08\x07\x00\x00\x00',  # 89  Y
        b'\x61\x51\x49\x45\x43\x00\x00\x00',  # 90  Z
        b'\x00\x7F\x41\x41\x00\x00\x00\x00',  # 91  [
        b'\x02\x04\x08\x10\x20\x00\x00\x00',  # 92  backslash
        b'\x00\x41\x41\x7F\x00\x00\x00\x00',  # 93  ]
        b'\x04\x02\x01\x02\x04\x00\x00\x00',  # 94  ^
        b'\x40\x40\x40\x40\x40\x00\x00\x00',  # 95  _
        b'\x00\x01\x02\x04\x00\x00\x00\x00',  # 96  `
        b'\x20\x54\x54\x54\x78\x00\x00\x00',  # 97  a
        b'\x7F\x48\x44\x44\x38\x00\x00\x00',  # 98  b
        b'\x38\x44\x44\x44\x20\x00\x00\x00',  # 99  c
        b'\x38\x44\x44\x48\x7F\x00\x00\x00',  # 100 d
        b'\x38\x54\x54\x54\x18\x00\x00\x00',  # 101 e
        b'\x08\x7E\x09\x01\x02\x00\x00\x00',  # 102 f
        b'\x0C\x52\x52\x52\x3E\x00\x00\x00',  # 103 g
        b'\x7F\x08\x04\x04\x78\x00\x00\x00',  # 104 h
        b'\x00\x44\x7D\x40\x00\x00\x00\x00',  # 105 i
        b'\x20\x40\x44\x3D\x00\x00\x00\x00',  # 106 j
        b'\x7F\x10\x28\x44\x00\x00\x00\x00',  # 107 k
        b'\x00\x41\x7F\x40\x00\x00\x00\x00',  # 108 l
        b'\x7C\x04\x18\x04\x78\x00\x00\x00',  # 109 m
        b'\x7C\x08\x04\x04\x78\x00\x00\x00',  # 110 n
        b'\x38\x44\x44\x44\x38\x00\x00\x00',  # 111 o
        b'\x7C\x14\x14\x14\x08\x00\x00\x00',  # 112 p
        b'\x08\x14\x14\x18\x7C\x00\x00\x00',  # 113 q
        b'\x7C\x08\x04\x04\x08\x00\x00\x00',  # 114 r
        b'\x48\x54\x54\x54\x20\x00\x00\x00',  # 115 s
        b'\x04\x3F\x44\x40\x20\x00\x00\x00',  # 116 t
        b'\x3C\x40\x40\x20\x7C\x00\x00\x00',  # 117 u
        b'\x1C\x20\x40\x20\x1C\x00\x00\x00',  # 118 v
        b'\x3C\x40\x30\x40\x3C\x00\x00\x00',  # 119 w
        b'\x44\x28\x10\x28\x44\x00\x00\x00',  # 120 x
        b'\x0C\x50\x50\x50\x3C\x00\x00\x00',  # 121 y
        b'\x44\x64\x54\x4C\x44\x00\x00\x00',  # 122 z
        b'\x00\x08\x36\x41\x00\x00\x00\x00',  # 123 {
        b'\x00\x00\x7F\x00\x00\x00\x00\x00',  # 124 |
        b'\x00\x41\x36\x08\x00\x00\x00\x00',  # 125 }
        b'\x10\x08\x08\x10\x08\x00\x00\x00',  # 126 ~
        b'\x00\x00\x00\x00\x00\x00\x00\x00',  # 127 DEL (blank)
    )
    # fmt: on

    def text_scaled(self, string, x, y, height, color=1, bg=0, spacing=1):
        """
        Draw text at (x, y) scaled to *height* pixels tall.

        Parameters
        ----------
        string  : text to draw
        x, y    : top-left corner
        height  : desired character height in pixels (minimum 8)
        color   : foreground pixel value (default 1 = on)
        bg      : background pixel value (default 0 = off)
                  set bg=-1 to leave background pixels untouched (transparent)
        spacing : extra pixels between characters (default 1)

        Returns the x coordinate just after the last character,
        useful for chaining multiple calls on the same line.

        The built-in 8x8 font is scaled using nearest-neighbour so characters
        stay crisp at integer multiples (16, 24, 32 …) but look fine at any size.

        Example
        -------
            oled.text_scaled("Hello!", 0, 0, 24)          # ~24px tall
            oled.text_scaled("Score: 99", 0, 30, 16)      # ~16px tall
            oled.text_scaled("!", 110, 0, 32, color=1, bg=0)
        """
        if height < 1:
            height = 1

        # Scale factor: font is 8 rows tall, 5 cols wide (+ 1 gap = 6 advance)
        # We scale both axes uniformly so char width = round(5 * height / 8)
        char_h = height
        char_w = max(1, (5 * height + 4) // 8)   # integer, rounds up slightly
        adv    = char_w + spacing                  # pixels to advance per char


        cx = x
        for ch in string:
            code = ord(ch)
            if code < 32 or code > 127:
                code = 32   # replace unknown chars with space
            glyph = self._FONT[code - 32]   # 8 bytes, columns 0-4 then 3 zeros

            # Render each destination pixel
            for dy in range(char_h):
                # Map dest row -> source row (0-7)
                src_row = (dy * 8) // char_h
                for dx in range(char_w):
                    # Map dest col -> source col (0-4)
                    src_col = (dx * 5) // char_w
                    # In the font each byte is a COLUMN (not a row):
                    # glyph[col] bit 0 = top row, bit 6 = bottom row
                    col_byte = glyph[src_col]
                    pixel_on = (col_byte >> src_row) & 1
                    val = color if pixel_on else bg
                    if val != -1:
                        self.pixel(cx + dx, y + dy, val)

            cx += adv

        return cx   # x position after last character
