"""
Monopoly for the Waveshare Pico-LCD-1.3 (Pico 2 / Pico 2 W)

FEATURES
  - Full 40-tile board, buying, rent, houses, jail, Chance/Community Chest,
    bankruptcy (same rules as before).
  - Save/Load: game state is written to flash (monopoly_save.json) and
    autosaved after every turn-changing event, so pulling power only loses
    at most the action in progress.
  - Smooth movement: tokens hop tile-by-tile around the board instead of
    teleporting.
  - Message text word-wraps instead of getting cut off.
  - Local "pass the Pico" multiplayer: choose 1-4 human players at startup;
    remaining slots are bots.
  - Optional wireless multiplayer over ESP-NOW: set WIRELESS = True below.
    Needs a Pico W / Pico 2 W (wireless silicon) on every board involved.
    One board is the HOST (runs the real game + a local display), the rest
    are CLIENTs (their own display, send button presses to the host, and
    show whatever the host broadcasts). This part is inherently harder to
    test without real hardware in hand, so treat it as a solid starting
    point you may need to tweak for your exact MicroPython firmware's
    espnow API.

CONTROLS (per human player, local or remote)
  A button      - roll dice / confirm (buy: yes) / jail: pay $50
  B button      - decline (buy: no) / jail: try to roll doubles
  X button      - open Build Houses menu (only before rolling)
  Y button      - open Portfolio (your properties)
  Joystick U/D  - scroll a menu when one is open, or change a setup value
  Joystick ctrl - pause / unpause

Save as main.py to run on boot, or run directly from Thonny.
"""

from machine import Pin, SPI, PWM
import framebuf
import time
import random
import json

# ----------------------------------------------------------------------------
# CONFIG - pins per the Waveshare Pico-LCD-1.3 wiki
# ----------------------------------------------------------------------------
LCD_DC   = 8
LCD_CS   = 9
LCD_SCK  = 10
LCD_MOSI = 11
LCD_RST  = 12
LCD_BL   = 13

JOY_UP    = 2
JOY_DOWN  = 18
JOY_LEFT  = 16
JOY_RIGHT = 20
JOY_CTRL  = 3

BTN_A = 15
BTN_B = 17
BTN_X = 19
BTN_Y = 21

WIDTH  = 240
HEIGHT = 240

# Rotation: 0, 90, 180, or 270 (degrees, clockwise). Adjust if the picture
# comes up sideways on your panel.
ROTATION = 90

NUM_PLAYERS = 4          # fixed number of board slots (some may be bots)
STARTING_CASH = 1500
NUM_SAVE_SLOTS = 3
SAVE_FILE_PATTERN = "monopoly_save_{}.json"
MOVE_STEP_MS = 90        # delay per tile hopped during movement animation
BOT_THINK_MS = 1000      # pause between each bot action so you can follow along

# --- Wireless multiplayer switch -------------------------------------------
# Set WIRELESS = True to enable ESP-NOW play across multiple Pico W/2 W
# boards. Leave False for a normal single-board game (local/bots only).
WIRELESS = False
WIRELESS_ROLE = "host"   # "host" (runs the game) or "client" (remote display)
# -----------------------------------------------------------------------------


def rgb(r, g, b):
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    # The panel expects pixel bytes in the opposite order from how
    # framebuf.RGB565 stores them (without this, hues come out rotated:
    # yellow shows blue, blue shows grey, red shows lime). Byte-swap once
    # here so normal RGB math works everywhere else in this file.
    return ((c & 0xFF) << 8) | (c >> 8)


def _sw(c):
    return ((c & 0xFF) << 8) | (c >> 8)


BLACK  = 0x0000
WHITE  = 0xFFFF
GRAY   = _sw(0x8410)
DKGRAY = _sw(0x39E7)

BROWN    = rgb(139, 69, 19)
LTBLUE   = rgb(135, 206, 235)
PINK     = rgb(255, 105, 180)
ORANGE   = rgb(255, 140, 0)
REDC     = rgb(220, 20, 60)
YELLOWC  = rgb(255, 215, 0)
GREENC   = rgb(34, 139, 34)
DKBLUE   = rgb(25, 25, 112)
WATERBLUE = rgb(70, 130, 220)
BLUEC = rgb(30, 100, 220)   # whistle icon color for Go To Jail
SPECIAL  = WHITE   # base color for the plain "grey" special tiles

PLAYER_COLORS = [WHITE, _sw(0x07FF), _sw(0xF81F), _sw(0xFFE0)]  # white, cyan, magenta, yellow
PLAYER_NAMES = ["You", "Bot A", "Bot B", "Bot C"]
TOKEN_OUTLINE = BLACK

BUTTON_ORDER = ["up", "down", "left", "right", "ctrl", "a", "b", "x", "y"]

# ----------------------------------------------------------------------------
# Board data: 40 tiles.
# type: go, property, railroad, utility, chance, chest, tax, jail, freepark, gotojail
# rent list index = number of houses (0-4), index 5 = hotel
# ----------------------------------------------------------------------------
TILES = [
    {"name": "GO", "type": "go"},
    {"name": "Mediterranean Ave", "type": "property", "group": "brown", "price": 60,
     "rent": [2, 10, 30, 90, 160, 250], "house_cost": 50},
    {"name": "Community Chest", "type": "chest"},
    {"name": "Baltic Ave", "type": "property", "group": "brown", "price": 60,
     "rent": [4, 20, 60, 180, 320, 450], "house_cost": 50},
    {"name": "Income Tax", "type": "tax", "amount": 200},
    {"name": "Reading Railroad", "type": "railroad", "price": 200},
    {"name": "Oriental Ave", "type": "property", "group": "ltblue", "price": 100,
     "rent": [6, 30, 90, 270, 400, 550], "house_cost": 50},
    {"name": "Chance", "type": "chance"},
    {"name": "Vermont Ave", "type": "property", "group": "ltblue", "price": 100,
     "rent": [6, 30, 90, 270, 400, 550], "house_cost": 50},
    {"name": "Connecticut Ave", "type": "property", "group": "ltblue", "price": 120,
     "rent": [8, 40, 100, 300, 450, 600], "house_cost": 50},
    {"name": "Jail (visiting)", "type": "jail"},
    {"name": "St. Charles Pl", "type": "property", "group": "pink", "price": 140,
     "rent": [10, 50, 150, 450, 625, 750], "house_cost": 100},
    {"name": "Electric Company", "type": "utility", "price": 150},
    {"name": "States Ave", "type": "property", "group": "pink", "price": 140,
     "rent": [10, 50, 150, 450, 625, 750], "house_cost": 100},
    {"name": "Virginia Ave", "type": "property", "group": "pink", "price": 160,
     "rent": [12, 60, 180, 500, 700, 900], "house_cost": 100},
    {"name": "Pennsylvania RR", "type": "railroad", "price": 200},
    {"name": "St. James Pl", "type": "property", "group": "orange", "price": 180,
     "rent": [14, 70, 200, 550, 750, 950], "house_cost": 100},
    {"name": "Community Chest", "type": "chest"},
    {"name": "Tennessee Ave", "type": "property", "group": "orange", "price": 180,
     "rent": [14, 70, 200, 550, 750, 950], "house_cost": 100},
    {"name": "New York Ave", "type": "property", "group": "orange", "price": 200,
     "rent": [16, 80, 220, 600, 800, 1000], "house_cost": 100},
    {"name": "Free Parking", "type": "freepark"},
    {"name": "Kentucky Ave", "type": "property", "group": "red", "price": 220,
     "rent": [18, 90, 250, 700, 875, 1050], "house_cost": 150},
    {"name": "Chance", "type": "chance"},
    {"name": "Indiana Ave", "type": "property", "group": "red", "price": 220,
     "rent": [18, 90, 250, 700, 875, 1050], "house_cost": 150},
    {"name": "Illinois Ave", "type": "property", "group": "red", "price": 240,
     "rent": [20, 100, 300, 750, 925, 1100], "house_cost": 150},
    {"name": "B&O Railroad", "type": "railroad", "price": 200},
    {"name": "Atlantic Ave", "type": "property", "group": "yellow", "price": 260,
     "rent": [22, 110, 330, 800, 975, 1150], "house_cost": 150},
    {"name": "Ventnor Ave", "type": "property", "group": "yellow", "price": 260,
     "rent": [22, 110, 330, 800, 975, 1150], "house_cost": 150},
    {"name": "Water Works", "type": "utility", "price": 150},
    {"name": "Marvin Gardens", "type": "property", "group": "yellow", "price": 280,
     "rent": [24, 120, 360, 850, 1025, 1200], "house_cost": 150},
    {"name": "Go To Jail", "type": "gotojail"},
    {"name": "Pacific Ave", "type": "property", "group": "green", "price": 300,
     "rent": [26, 130, 390, 900, 1100, 1275], "house_cost": 200},
    {"name": "North Carolina Ave", "type": "property", "group": "green", "price": 300,
     "rent": [26, 130, 390, 900, 1100, 1275], "house_cost": 200},
    {"name": "Community Chest", "type": "chest"},
    {"name": "Pennsylvania Ave", "type": "property", "group": "green", "price": 320,
     "rent": [28, 150, 450, 1000, 1200, 1400], "house_cost": 200},
    {"name": "Short Line", "type": "railroad", "price": 200},
    {"name": "Chance", "type": "chance"},
    {"name": "Park Place", "type": "property", "group": "dkblue", "price": 350,
     "rent": [35, 175, 500, 1100, 1300, 1500], "house_cost": 200},
    {"name": "Luxury Tax", "type": "tax", "amount": 100},
    {"name": "Boardwalk", "type": "property", "group": "dkblue", "price": 400,
     "rent": [50, 200, 600, 1400, 1700, 2000], "house_cost": 200},
]

GROUP_COLOR = {
    "brown": BROWN, "ltblue": LTBLUE, "pink": PINK, "orange": ORANGE,
    "red": REDC, "yellow": YELLOWC, "green": GREENC, "dkblue": DKBLUE,
}

CHANCE_CARDS = [
    ("Advance to GO. Collect $200", "go", 0),
    ("Bank pays dividend of $50", "cash", 50),
    ("Pay poor tax of $15", "cash", -15),
    ("Go to Jail", "jail", 0),
    ("Get out of Jail Free", "gojf", 0),
    ("Pay each player $50", "payall", -50),
    ("Collect $150 in a contest", "cash", 150),
    ("Advance to Boardwalk", "goto", 39),
]

CHEST_CARDS = [
    ("Advance to GO. Collect $200", "go", 0),
    ("Bank error in your favor: $200", "cash", 200),
    ("Doctor's fee: pay $50", "cash", -50),
    ("Go to Jail", "jail", 0),
    ("Get out of Jail Free", "gojf", 0),
    ("Collect $100 from each player", "collectall", 100),
    ("Life insurance matures: $100", "cash", 100),
    ("Pay hospital fees $100", "cash", -100),
]

GOJF_CARD = ("Get out of Jail Free", "gojf", 0)

# Real decks, not just "pick any of these 8 at random every time" -- each
# deck holds exactly one copy of each card. A drawn card goes to the
# bottom of its deck afterward EXCEPT Get Out of Jail Free, which leaves
# the deck entirely and sits with whoever drew it until they use it (at
# which point it's returned to the bottom). This is what keeps there from
# ever being more than one "Get Out of Jail Free" in play per deck.
CHANCE_DECK = []
CHEST_DECK = []


def build_decks():
    global CHANCE_DECK, CHEST_DECK
    CHANCE_DECK = shuffled(list(CHANCE_CARDS))
    CHEST_DECK = shuffled(list(CHEST_CARDS))


def shuffled(lst):
    """Manual Fisher-Yates -- MicroPython's lightweight 'random' module
    doesn't reliably provide random.shuffle, unlike desktop CPython."""
    lst = list(lst)
    for i in range(len(lst) - 1, 0, -1):
        j = random.randint(0, i)
        lst[i], lst[j] = lst[j], lst[i]
    return lst


def draw_card(deck):
    card = deck.pop(0)
    if card[1] != "gojf":
        deck.append(card)
    return card


def wrap_text(text, width):
    """Greedy word-wrap. Returns a list of lines each <= width chars."""
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            while len(w) > width:
                lines.append(w[:width])
                w = w[width:]
            cur = w
    if cur:
        lines.append(cur)
    return lines


def tile_bg_color(tile):
    ttype = tile["type"]
    if ttype == "property":
        return GROUP_COLOR[tile["group"]]
    if ttype == "utility":
        return YELLOWC if "Electric" in tile["name"] else WATERBLUE
    if ttype in ("jail", "gotojail"):
        return ORANGE
    return SPECIAL  # railroad, chance, chest, tax, freepark, go -> white


def draw_owner_marker(lcd, x, y, cell, owner):
    """Small flag in the tile's corner showing who owns it, with a black
    backing square so it stays visible even when the player's color is
    the same as the tile's own background (e.g. white railroads owned by
    the white player)."""
    fs = 7
    lcd.fill_rect(x + 1, y + 1, fs, fs, BLACK)
    lcd.fill_rect(x + 2, y + 2, fs - 2, fs - 2, PLAYER_COLORS[owner])


def grid_pos(i):
    """Map a board index (0-39) to (row, col) on an 11x11 grid."""
    if i <= 10:
        return 10, 10 - i
    elif i <= 20:
        return 20 - i, 0
    elif i <= 30:
        return 0, i - 20
    else:
        return i - 30, 10


def draw_tile_icon(lcd, x, y, cell, tile):
    """Small pixel-drawn symbol so the plain-color tiles are identifiable
    at a glance instead of just a blank block."""
    cx = x + cell // 2
    cy = y + cell // 2
    ttype = tile["type"]

    if ttype == "chance":
        lcd.text("?", cx - 4, cy - 4, BLACK)

    elif ttype == "chest":
        bx, by = x + 5, y + 7
        bw, bh = cell - 10, 9
        lcd.rect(bx, by, bw, bh, BLACK)
        lcd.hline(bx, by + 3, bw, BLACK)
        lcd.fill_rect(cx - 1, by + 1, 2, 2, BLACK)

    elif ttype == "railroad":
        # side-on locomotive: smokestack + cab + long body + wheels
        bx, by = x + 3, y + 11
        bw, bh = cell - 7, 5
        lcd.fill_rect(bx, by, bw, bh, BLACK)                  # boiler/body
        lcd.fill_rect(bx, by - 5, 6, 5, BLACK)                # cab, front-left
        lcd.fill_rect(bx + 1, by - 8, 2, 3, BLACK)             # smokestack
        lcd.ellipse(bx + 3, by + bh, 2, 2, BLACK, True)        # front wheel
        lcd.ellipse(bx + bw - 3, by + bh, 2, 2, BLACK, True)   # rear wheel

    elif ttype == "utility":
        if "Electric" in tile["name"]:
            lcd.line(cx, y + 3, cx - 3, cy, BLACK)
            lcd.line(cx - 3, cy, cx + 1, cy, BLACK)
            lcd.line(cx + 1, cy, cx - 2, y + cell - 3, BLACK)
        else:
            # teardrop: tapered point widening down into a round body,
            # built from stacked horizontal rows so it reads as a shape
            # instead of just a dot
            apex_y = cy - 7
            for row in range(6):
                yy = apex_y + row
                hw = min(row, 4)
                if hw == 0:
                    lcd.pixel(cx, yy, BLACK)
                else:
                    lcd.hline(cx - hw, yy, hw * 2 + 1, BLACK)
            lcd.ellipse(cx, cy + 2, 4, 4, BLACK, True)

    elif ttype == "tax":
        lcd.text("$", cx - 4, cy - 4, BLACK)

    elif ttype == "jail":
        for dx in (-4, 0, 4):
            lcd.vline(cx + dx, y + 4, cell - 8, BLACK)

    elif ttype == "gotojail":
        # blue referee's whistle: round chamber + mouthpiece barrel
        lcd.ellipse(cx - 2, cy, 4, 3, BLUEC, True)
        lcd.fill_rect(cx, cy - 1, 6, 3, BLUEC)
        lcd.ellipse(cx + 6, cy, 1, 1, BLACK, True)

    elif ttype == "freepark":
        lcd.text("P", cx - 4, cy - 4, BLACK)

    elif ttype == "go":
        lcd.fill_rect(cx - 6, cy - 1, 7, 2, REDC)             # shaft
        lcd.line(cx + 1, cy - 4, cx + 6, cy, REDC)             # upper head
        lcd.line(cx + 1, cy + 4, cx + 6, cy, REDC)             # lower head
        lcd.line(cx + 1, cy - 4, cx + 1, cy + 4, REDC)         # back of head


# ----------------------------------------------------------------------------
# ST7789 driver (minimal, framebuf-backed)
# ----------------------------------------------------------------------------
class ST7789(framebuf.FrameBuffer):
    _ROTATIONS = {
        0:   (0x00, False),
        90:  (0x60, True),
        180: (0xC0, False),
        270: (0xA0, True),
    }

    def __init__(self, spi, cs, dc, rst, bl, width=WIDTH, height=HEIGHT,
                 rotation=ROTATION):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.bl = bl

        self._madctl, swapped = self._ROTATIONS[rotation]
        if swapped:
            self.width, self.height = height, width
        else:
            self.width, self.height = width, height

        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=1)

        self.buffer = bytearray(self.width * self.height * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)

        self.pwm_bl = PWM(self.bl)
        self.pwm_bl.freq(1000)
        self.brightness(80)

        self._init_display()

    def _write_cmd(self, cmd):
        self.cs(1); self.dc(0); self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def _write_data(self, data):
        self.cs(1); self.dc(1); self.cs(0)
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
        self.cs(1)

    def brightness(self, pct):
        pct = max(0, min(100, pct))
        self.pwm_bl.duty_u16(int(pct / 100 * 65535))

    def _init_display(self):
        self.rst(1); time.sleep_ms(50)
        self.rst(0); time.sleep_ms(50)
        self.rst(1); time.sleep_ms(150)

        self._write_cmd(0x36); self._write_data(self._madctl)
        self._write_cmd(0x3A); self._write_data(0x05)
        self._write_cmd(0xB2); self._write_data(b'\x0C\x0C\x00\x33\x33')
        self._write_cmd(0xB7); self._write_data(0x35)
        self._write_cmd(0xBB); self._write_data(0x19)
        self._write_cmd(0xC0); self._write_data(0x2C)
        self._write_cmd(0xC2); self._write_data(0x01)
        self._write_cmd(0xC3); self._write_data(0x12)
        self._write_cmd(0xC4); self._write_data(0x20)
        self._write_cmd(0xC6); self._write_data(0x0F)
        self._write_cmd(0xD0); self._write_data(b'\xA4\xA1')
        self._write_cmd(0xE0); self._write_data(b'\xD0\x04\x0D\x11\x13\x2B\x3F\x54\x4C\x18\x0D\x0B\x1F\x23')
        self._write_cmd(0xE1); self._write_data(b'\xD0\x04\x0C\x11\x13\x2C\x3F\x44\x51\x2F\x1F\x1F\x20\x23')
        self._write_cmd(0x21)
        self._write_cmd(0x11); time.sleep_ms(120)
        self._write_cmd(0x29)

    def _set_window(self, x0, y0, x1, y1):
        self._write_cmd(0x2A); self._write_data(bytearray([0x00, x0, 0x00, x1]))
        self._write_cmd(0x2B); self._write_data(bytearray([0x00, y0, 0x00, y1]))
        self._write_cmd(0x2C)

    def show(self):
        self._set_window(0, 0, self.width - 1, self.height - 1)
        self.cs(1); self.dc(1); self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)


# ----------------------------------------------------------------------------
# Input helper, with simple edge-detected "just pressed" tracking
# ----------------------------------------------------------------------------
class Controls:
    def __init__(self):
        self.up    = Pin(JOY_UP,    Pin.IN, Pin.PULL_UP)
        self.down  = Pin(JOY_DOWN,  Pin.IN, Pin.PULL_UP)
        self.left  = Pin(JOY_LEFT,  Pin.IN, Pin.PULL_UP)
        self.right = Pin(JOY_RIGHT, Pin.IN, Pin.PULL_UP)
        self.ctrl  = Pin(JOY_CTRL,  Pin.IN, Pin.PULL_UP)
        self.btn_a = Pin(BTN_A, Pin.IN, Pin.PULL_UP)
        self.btn_b = Pin(BTN_B, Pin.IN, Pin.PULL_UP)
        self.btn_x = Pin(BTN_X, Pin.IN, Pin.PULL_UP)
        self.btn_y = Pin(BTN_Y, Pin.IN, Pin.PULL_UP)
        self._prev = {}

    def raw(self):
        return {
            "up": not self.up.value(), "down": not self.down.value(),
            "left": not self.left.value(), "right": not self.right.value(),
            "ctrl": not self.ctrl.value(),
            "a": not self.btn_a.value(), "b": not self.btn_b.value(),
            "x": not self.btn_x.value(), "y": not self.btn_y.value(),
        }

    def pressed(self):
        """Returns only newly-pressed buttons this call (edge triggered)."""
        cur = self.raw()
        out = {}
        for k, v in cur.items():
            out[k] = v and not self._prev.get(k, False)
        self._prev = cur
        return out


def pack_buttons(keys):
    bm = 0
    for i, name in enumerate(BUTTON_ORDER):
        if keys.get(name):
            bm |= (1 << i)
    return bm


def unpack_buttons(bm):
    return {name: bool(bm & (1 << i)) for i, name in enumerate(BUTTON_ORDER)}



def main():
    spi = SPI(1,
              baudrate=40_000_000,
              polarity=0,
              phase=0,
              sck=Pin(LCD_SCK),
              mosi=Pin(LCD_MOSI))

    lcd = ST7789(spi,
                 cs=Pin(LCD_CS),
                 dc=Pin(LCD_DC),
                 rst=Pin(LCD_RST),
                 bl=Pin(LCD_BL))

    ctrl = Controls()

    


if __name__ == "__main__":
    main()