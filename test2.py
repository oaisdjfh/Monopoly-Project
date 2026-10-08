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


# ----------------------------------------------------------------------------
# Player
# ----------------------------------------------------------------------------
class Player:
    def __init__(self, idx, is_bot):
        self.idx = idx
        self.is_bot = is_bot
        self.cash = STARTING_CASH
        self.pos = 0
        self.in_jail = False
        self.jail_turns = 0
        self.gojf_chance = False   # holding the Chance deck's Get Out of Jail Free
        self.gojf_chest = False    # holding the Chest deck's Get Out of Jail Free
        self.bankrupt = False

    def properties(self):
        return [i for i in range(40) if OWNER[i] == self.idx]

    def to_dict(self):
        return {
            "cash": self.cash, "pos": self.pos, "in_jail": self.in_jail,
            "jail_turns": self.jail_turns,
            "gojf_chance": self.gojf_chance, "gojf_chest": self.gojf_chest,
            "bankrupt": self.bankrupt, "is_bot": self.is_bot,
        }

    @classmethod
    def from_dict(cls, idx, d):
        p = cls(idx, d.get("is_bot", idx != 0))
        p.cash = d.get("cash", STARTING_CASH)
        p.pos = d.get("pos", 0)
        p.in_jail = d.get("in_jail", False)
        p.jail_turns = d.get("jail_turns", 0)
        p.gojf_chance = d.get("gojf_chance", False)
        p.gojf_chest = d.get("gojf_chest", False)
        p.bankrupt = d.get("bankrupt", False)
        return p


# ----------------------------------------------------------------------------
# Global ownership state (kept outside Player so rent calc can scan easily)
# ----------------------------------------------------------------------------
OWNER = [None] * 40      # player idx or None
HOUSES = [0] * 40        # 0-4 houses, 5 = hotel
MORTGAGED = [False] * 40


def owns_full_group(player_idx, group):
    members = [i for i, t in enumerate(TILES)
               if t["type"] == "property" and t.get("group") == group]
    return all(OWNER[i] == player_idx for i in members)


def calc_rent(idx, dice_sum, owner_idx):
    tile = TILES[idx]
    if tile["type"] == "property":
        h = HOUSES[idx]
        base = tile["rent"][h]
        if h == 0 and owns_full_group(owner_idx, tile["group"]):
            return base * 2
        return base
    if tile["type"] == "railroad":
        count = sum(1 for i, t in enumerate(TILES)
                    if t["type"] == "railroad" and OWNER[i] == owner_idx)
        return 25 * (2 ** (count - 1))
    if tile["type"] == "utility":
        count = sum(1 for i, t in enumerate(TILES)
                    if t["type"] == "utility" and OWNER[i] == owner_idx)
        mult = 10 if count >= 2 else 4
        return dice_sum * mult
    return 0


def raise_cash(player, amount):
    """Try to mortgage properties until player has >= amount or nothing left."""
    while player.cash < amount:
        props = [i for i in player.properties() if not MORTGAGED[i] and HOUSES[i] == 0]
        if not props:
            break
        i = props[0]
        MORTGAGED[i] = True
        player.cash += TILES[i]["price"] // 2
    return player.cash >= amount


def player_go_bankrupt(player):
    player.bankrupt = True
    for i in player.properties():
        OWNER[i] = None
        HOUSES[i] = 0
        MORTGAGED[i] = False


# ----------------------------------------------------------------------------
# Save / load
# ----------------------------------------------------------------------------
def game_to_dict(game):
    return {
        "turn": game.turn,
        "doubles_count": game.doubles_count,
        "state": game.state if game.state in ("TURN_START", "TURN_END", "JAIL_CHOICE") else "TURN_START",
        "players": [p.to_dict() for p in game.players],
        "owner": OWNER, "houses": HOUSES, "mortgaged": MORTGAGED,
        "chance_deck": CHANCE_DECK, "chest_deck": CHEST_DECK,
    }


def save_game(game):
    fn = SAVE_FILE_PATTERN.format(game.save_slot)
    try:
        with open(fn, "w") as f:
            json.dump(game_to_dict(game), f)
        return True
    except OSError:
        return False


def save_file_exists(slot):
    try:
        with open(SAVE_FILE_PATTERN.format(slot)):
            return True
    except OSError:
        return False


def delete_save(slot):
    try:
        import os
        os.remove(SAVE_FILE_PATTERN.format(slot))
    except (OSError, ImportError):
        pass


def load_game(lcd, ctrl, slot):
    global OWNER, HOUSES, MORTGAGED, CHANCE_DECK, CHEST_DECK
    try:
        with open(SAVE_FILE_PATTERN.format(slot)) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None

    OWNER = data["owner"]
    HOUSES = data["houses"]
    MORTGAGED = data["mortgaged"]
    # Decks are persisted so a reload can't accidentally reintroduce a
    # second copy of a Get Out of Jail Free card that's already held by a
    # player. Older saves won't have this key -- rebuild fresh in that case.
    if "chance_deck" in data and "chest_deck" in data and data["chance_deck"] and data["chest_deck"]:
        CHANCE_DECK = data["chance_deck"]
        CHEST_DECK = data["chest_deck"]
    else:
        build_decks()
    players = [Player.from_dict(i, pd) for i, pd in enumerate(data["players"])]
    game = Game(lcd, ctrl, players)
    game.save_slot = slot
    game.turn = data.get("turn", 0)
    game.doubles_count = data.get("doubles_count", 0)
    game.state = data.get("state", "TURN_START")
    game.log("Save loaded.", "{}'s turn. A: roll".format(PLAYER_NAMES[game.turn]))
    return game


# ----------------------------------------------------------------------------
# The game
# ----------------------------------------------------------------------------
class Game:
    def __init__(self, lcd, ctrl, players):
        self.lcd = lcd
        self.ctrl = ctrl
        self.players = players
        self.turn = 0
        self.doubles_count = 0
        self.state = "TURN_START"
        self.msg = ["Welcome to Monopoly!", "Press A to roll."]
        self.dice = (1, 1)
        self.menu_items = []
        self.menu_sel = 0
        self.paused = False
        self.save_slot = 0

    # -- helpers --------------------------------------------------------
    def log(self, *lines):
        self.msg = list(lines)

    def current(self):
        return self.players[self.turn]

    def next_player(self):
        n = len(self.players)
        for step in range(1, n + 1):
            cand = (self.turn + step) % n
            if not self.players[cand].bankrupt:
                self.turn = cand
                return

    def active_players(self):
        return [p for p in self.players if not p.bankrupt]

    def autosave(self):
        save_game(self)

    # -- movement animation --------------------------------------------------------
    def animate_move(self, p, steps):
        """Hop the token forward tile-by-tile, redrawing each step. Returns
        True if the player passed or landed on GO (which pays $200)."""
        passed_go = False
        for _ in range(int(steps)):
            p.pos = (p.pos + 1) % 40
            if p.pos == 0:
                p.cash += 200
                passed_go = True
            self.draw()
            time.sleep_ms(MOVE_STEP_MS)
        return passed_go

    # -- turn flow --------------------------------------------------------
    def start_turn(self):
        p = self.current()
        self.doubles_count = 0
        if p.in_jail:
            self.state = "JAIL_CHOICE"
            if p.gojf_chance or p.gojf_chest:
                self.log("{} is in Jail.".format(PLAYER_NAMES[p.idx]),
                         "A:pay $50 B:doubles X:use card")
            else:
                self.log("{} is in Jail.".format(PLAYER_NAMES[p.idx]),
                         "A: pay $50  B: roll doubles")
        else:
            self.state = "TURN_START"
            self.log("{}'s turn. Cash ${}".format(PLAYER_NAMES[p.idx], p.cash),
                     "A: roll dice")

    def roll_dice(self):
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        self.dice = (d1, d2)
        if d1 == d2:
            self.doubles_count += 1
        return d1, d2

    def do_roll(self):
        p = self.current()
        d1, d2 = self.roll_dice()
        total = d1 + d2

        if d1 == d2 and self.doubles_count >= 3:
            p.in_jail = True
            p.pos = 10
            self.log("{} rolled 3 doubles!".format(PLAYER_NAMES[p.idx]),
                     "Sent straight to Jail.")
            self.state = "TURN_END"
            self.autosave()
            return

        self.log("Rolled {} + {} = {}".format(d1, d2, total))
        self.draw()
        time.sleep_ms(350)
        passed_go = self.animate_move(p, total)

        lines = ["Rolled {} + {} = {}".format(d1, d2, total)]
        if passed_go:
            lines.append("Passed GO, +$200")
        self.log(*lines)
        self.resolve_tile(p)
        self.autosave()

    def resolve_tile(self, p):
        tile = TILES[p.pos]
        ttype = tile["type"]
        name = tile["name"]

        if ttype in ("property", "railroad", "utility"):
            owner = OWNER[p.pos]
            if owner is None:
                self.state = "BUY_PROMPT"
                self.log("{}".format(name), "Price ${}".format(tile["price"]),
                         "A: buy   B: skip")
                return
            elif owner != p.idx and not MORTGAGED[p.pos]:
                rent = calc_rent(p.pos, sum(self.dice), owner)
                if not raise_cash(p, rent):
                    rent = p.cash
                    player_go_bankrupt(p)
                    self.log("{} landed on {}".format(PLAYER_NAMES[p.idx], name),
                             "Owed ${} - BANKRUPT!".format(rent))
                    self.players[owner].cash += rent
                    self.check_game_over()
                    self.state = "TURN_END"
                    return
                p.cash -= rent
                self.players[owner].cash += rent
                self.log("{} landed on {}".format(PLAYER_NAMES[p.idx], name),
                         "Paid ${} rent to {}".format(rent, PLAYER_NAMES[owner]))
            else:
                self.log("{} landed on own property".format(PLAYER_NAMES[p.idx]), name)
            self.state = "TURN_END"

        elif ttype == "tax":
            amt = tile["amount"]
            if not raise_cash(p, amt):
                amt = p.cash
                player_go_bankrupt(p)
                self.log("{} owed ${} tax".format(PLAYER_NAMES[p.idx], amt), "BANKRUPT!")
                self.check_game_over()
            else:
                p.cash -= amt
                self.log("{} paid ${} tax".format(PLAYER_NAMES[p.idx], amt))
            self.state = "TURN_END"

        elif ttype == "chance" or ttype == "chest":
            deck = CHANCE_DECK if ttype == "chance" else CHEST_DECK
            card = draw_card(deck)
            self.apply_card(p, card, ttype)

        elif ttype == "gotojail":
            p.in_jail = True
            p.pos = 10
            self.log("{} -> Go To Jail!".format(PLAYER_NAMES[p.idx]))
            self.state = "TURN_END"

        elif ttype == "jail" or ttype == "freepark" or ttype == "go":
            self.log("{} is on {}".format(PLAYER_NAMES[p.idx], name))
            self.state = "TURN_END"

        else:
            self.state = "TURN_END"

    def apply_card(self, p, card, deck_name):
        text, kind, val = card
        lines = [text]

        if kind == "cash":
            if val < 0 and not raise_cash(p, -val):
                player_go_bankrupt(p)
                lines.append("BANKRUPT!")
                self.check_game_over()
            else:
                p.cash += val
            self.log(*lines)
            self.state = "TURN_END"

        elif kind == "go":
            self.log(*lines)
            if p.pos != 0:
                self.draw()
                time.sleep_ms(300)
                steps = (0 - p.pos) % 40
                self.animate_move(p, steps)
            else:
                p.cash += 200
            self.state = "TURN_END"

        elif kind == "goto":
            self.log(*lines)
            if p.pos != val:
                self.draw()
                time.sleep_ms(300)
                steps = (val - p.pos) % 40
                passed_go = self.animate_move(p, steps)
                if passed_go:
                    lines.append("Passed GO, +$200")
                    self.log(*lines)
            self.resolve_tile(p)
            return

        elif kind == "jail":
            p.in_jail = True
            p.pos = 10
            self.log(*lines)
            self.state = "TURN_END"

        elif kind == "gojf":
            if deck_name == "chance":
                p.gojf_chance = True
            else:
                p.gojf_chest = True
            self.log(*lines)
            self.state = "TURN_END"

        elif kind == "payall":
            for other in self.players:
                if other is not p and not other.bankrupt:
                    amt = -val
                    pay = min(amt, p.cash)
                    p.cash -= pay
                    other.cash += pay
            self.log(*lines)
            self.state = "TURN_END"

        elif kind == "collectall":
            for other in self.players:
                if other is not p and not other.bankrupt:
                    pay = min(val, other.cash)
                    other.cash -= pay
                    p.cash += pay
            self.log(*lines)
            self.state = "TURN_END"

        self.autosave()

    def jail_use_gojf(self, p):
        if p.gojf_chance:
            p.gojf_chance = False
            CHANCE_DECK.append(GOJF_CARD)
        elif p.gojf_chest:
            p.gojf_chest = False
            CHEST_DECK.append(GOJF_CARD)
        else:
            return
        p.in_jail = False
        p.jail_turns = 0
        self.log("{} used a Get Out of Jail Free card!".format(PLAYER_NAMES[p.idx]),
                 "A: roll dice")
        self.state = "TURN_START"
        self.autosave()

    def jail_pay(self, p):
        if p.cash >= 50:
            p.cash -= 50
            p.in_jail = False
            self.log("{} paid $50 bail.".format(PLAYER_NAMES[p.idx]), "A: roll dice")
            self.state = "TURN_START"
        else:
            self.log("Not enough cash!")
            self.state = "JAIL_CHOICE"
        self.autosave()

    def jail_try_doubles(self, p):
        d1, d2 = self.roll_dice()
        if d1 == d2:
            p.in_jail = False
            self.log("Rolled doubles ({},{})! Free.".format(d1, d2))
            self.draw()
            time.sleep_ms(350)
            passed_go = self.animate_move(p, d1 + d2)
            if passed_go:
                self.log("Rolled doubles! Free.", "Passed GO, +$200")
            self.resolve_tile(p)
        else:
            p.jail_turns += 1
            if p.jail_turns >= 3:
                p.in_jail = False
                p.jail_turns = 0
                p.cash -= 50
                self.log("3rd try failed. Pay $50, released.")
                self.draw()
                time.sleep_ms(350)
                passed_go = self.animate_move(p, d1 + d2)
                if passed_go:
                    self.log("Paid $50, released.", "Passed GO, +$200")
                self.resolve_tile(p)
            else:
                self.log("No doubles ({},{}).".format(d1, d2), "Still in Jail.")
                self.state = "TURN_END"
        self.autosave()

    def end_turn(self):
        p = self.current()
        if self.check_game_over():
            self.autosave()
            return
        if (not p.bankrupt) and (not p.in_jail) and self.dice[0] == self.dice[1] \
                and self.doubles_count > 0 and self.doubles_count < 3:
            self.log("Doubles! {} goes again.".format(PLAYER_NAMES[p.idx]), "A: roll dice")
            self.state = "TURN_START"
        else:
            self.next_player()
            self.start_turn()
        self.autosave()

    def check_game_over(self):
        active = self.active_players()
        if len(active) <= 1:
            winner = active[0] if active else None
            self.state = "GAME_OVER"
            if winner:
                self.log("GAME OVER", "{} wins!".format(PLAYER_NAMES[winner.idx]))
            else:
                self.log("GAME OVER")
            return True
        return False

    # -- bot AI --------------------------------------------------------
    def bot_take_turn(self):
        p = self.current()
        time.sleep_ms(BOT_THINK_MS)
        if p.in_jail:
            if p.gojf_chance or p.gojf_chest:
                self.jail_use_gojf(p)
            elif p.cash > 300:
                self.jail_pay(p)
            else:
                self.jail_try_doubles(p)
            self.draw()
            time.sleep_ms(BOT_THINK_MS)
            if self.state == "TURN_END":
                self.end_turn()
            return

        self.do_roll()
        self.draw()
        time.sleep_ms(BOT_THINK_MS)

        if self.state == "BUY_PROMPT":
            tile = TILES[p.pos]
            if p.cash - tile["price"] > 150:
                OWNER[p.pos] = p.idx
                p.cash -= tile["price"]
                self.log("{} bought {}".format(PLAYER_NAMES[p.idx], tile["name"]))
            else:
                self.log("{} skipped {}".format(PLAYER_NAMES[p.idx], tile["name"]))
            self.state = "TURN_END"
            self.autosave()
            self.draw()
            time.sleep_ms(BOT_THINK_MS)

        for group in GROUP_COLOR:
            if owns_full_group(p.idx, group) and p.cash > 400:
                members = [i for i, t in enumerate(TILES)
                           if t["type"] == "property" and t.get("group") == group]
                members.sort(key=lambda i: HOUSES[i])
                lowest = HOUSES[members[0]]
                if lowest < 5:
                    cost = TILES[members[0]]["house_cost"]
                    if p.cash - cost > 200:
                        HOUSES[members[0]] += 1
                        p.cash -= cost
                        self.autosave()
                        self.log("{} built a house on {}".format(
                            PLAYER_NAMES[p.idx], TILES[members[0]]["name"]))
                        self.draw()
                        time.sleep_ms(BOT_THINK_MS)

        if self.state == "TURN_END":
            self.end_turn()

    # -- input handling --------------------------------------------------------
    def handle_input(self, keys):
        if keys.get("ctrl"):
            self.paused = not self.paused
            return
        if self.paused:
            return
        if self.state == "GAME_OVER":
            return

        p = self.current()
        if p.is_bot:
            return  # bots act in the main loop, not via buttons

        if self.state == "TURN_START":
            if keys.get("a"):
                self.do_roll()
            elif keys.get("x"):
                self.open_build_menu()
            elif keys.get("y"):
                self.open_portfolio()

        elif self.state == "JAIL_CHOICE":
            if keys.get("a"):
                self.jail_pay(p)
            elif keys.get("b"):
                self.jail_try_doubles(p)
            elif keys.get("x") and (p.gojf_chance or p.gojf_chest):
                self.jail_use_gojf(p)

        elif self.state == "BUY_PROMPT":
            tile = TILES[p.pos]
            if keys.get("a"):
                if p.cash >= tile["price"]:
                    OWNER[p.pos] = p.idx
                    p.cash -= tile["price"]
                    self.log("Bought {}!".format(tile["name"]))
                else:
                    self.log("Not enough cash!")
                self.state = "TURN_END"
                self.autosave()
            elif keys.get("b"):
                self.log("Skipped {}".format(tile["name"]))
                self.state = "TURN_END"
                self.autosave()

        elif self.state == "TURN_END":
            if keys.get("a") or keys.get("b"):
                self.end_turn()

        elif self.state == "BUILD_MENU":
            if keys.get("up"):
                self.menu_sel = (self.menu_sel - 1) % max(1, len(self.menu_items))
            elif keys.get("down"):
                self.menu_sel = (self.menu_sel + 1) % max(1, len(self.menu_items))
            elif keys.get("a"):
                self.build_selected()
            elif keys.get("b") or keys.get("x"):
                self.state = "TURN_START"
                self.log("{}'s turn. Cash ${}".format(PLAYER_NAMES[p.idx], p.cash),
                         "A: roll dice")

        elif self.state == "PORTFOLIO":
            if keys.get("up"):
                self.menu_sel = (self.menu_sel - 1) % max(1, len(self.menu_items))
            elif keys.get("down"):
                self.menu_sel = (self.menu_sel + 1) % max(1, len(self.menu_items))
            elif keys.get("b") or keys.get("y"):
                self.state = "TURN_START"
                self.log("{}'s turn. Cash ${}".format(PLAYER_NAMES[p.idx], p.cash),
                         "A: roll dice")

    def open_build_menu(self):
        p = self.current()
        items = []
        for group in GROUP_COLOR:
            if owns_full_group(p.idx, group):
                members = [i for i, t in enumerate(TILES)
                           if t["type"] == "property" and t.get("group") == group]
                for i in members:
                    if HOUSES[i] < 5 and not MORTGAGED[i]:
                        items.append(i)
        if not items:
            self.log("No properties eligible", "(need full color group)")
            return
        self.menu_items = items
        self.menu_sel = 0
        self.state = "BUILD_MENU"

    def build_selected(self):
        p = self.current()
        if not self.menu_items:
            return
        i = self.menu_items[self.menu_sel]
        cost = TILES[i]["house_cost"]
        if p.cash >= cost:
            p.cash -= cost
            HOUSES[i] += 1
            self.log("Built on {}".format(TILES[i]["name"]),
                     "Cash ${}".format(p.cash))
            self.autosave()
        else:
            self.log("Not enough cash!")
        self.open_build_menu()
        if not self.menu_items:
            self.state = "TURN_START"

    def open_portfolio(self):
        p = self.current()
        self.menu_items = p.properties()
        self.menu_sel = 0
        self.state = "PORTFOLIO"

    # -- rendering --------------------------------------------------------
    def draw(self):
        lcd = self.lcd
        lcd.fill(BLACK)

        if self.state in ("BUILD_MENU", "PORTFOLIO"):
            self.draw_menu()
        else:
            self.draw_board()

        if self.paused:
            lcd.fill_rect(0, lcd.height // 2 - 10, lcd.width, 20, BLACK)
            lcd.text("PAUSED", lcd.width // 2 - 24, lcd.height // 2 - 4, WHITE)

        lcd.show()

    def draw_board(self):
        lcd = self.lcd
        cell = 21
        size = cell * 11
        ox = (lcd.width - size) // 2
        oy = (lcd.height - size) // 2

        for i, tile in enumerate(TILES):
            row, col = grid_pos(i)
            x = ox + col * cell
            y = oy + row * cell

            ttype = tile["type"]
            color = tile_bg_color(tile)

            owner = OWNER[i]
            lcd.fill_rect(x, y, cell - 1, cell - 1, color)
            if owner is not None:
                draw_owner_marker(lcd, x, y, cell, owner)

            if ttype != "property":
                draw_tile_icon(lcd, x, y, cell, tile)

        # info panel fills the hollow center of the board
        px = ox + cell
        py = oy + cell
        pw = size - 2 * cell
        ph = size - 2 * cell
        lcd.fill_rect(px, py, pw, ph, BLACK)

        char_w = (pw - 6) // 8
        hint_h = 10
        players_h = len(self.players) * 10
        msg_area_h = ph - hint_h - players_h - 6
        max_msg_lines = max(1, msg_area_h // 10)

        wrapped = []
        for m in self.msg:
            wrapped.extend(wrap_text(m, char_w))
        wrapped = wrapped[:max_msg_lines]

        ty = py + 3
        for line in wrapped:
            lcd.text(line, px + 3, ty, WHITE)
            ty += 10

        ty = py + 3 + max_msg_lines * 10 + 4
        for p in self.players:
            status = "BR" if p.bankrupt else "${}".format(p.cash)
            marker = ">" if p.idx == self.turn else " "
            lcd.text("{}{}: {}".format(marker, PLAYER_NAMES[p.idx], status),
                      px + 3, ty, PLAYER_COLORS[p.idx])
            ty += 10

        hint = self.hint_for_state()
        lcd.text(hint[:char_w], px + 3, py + ph - 10, DKGRAY)

        # player tokens, drawn last so they sit on top of everything
        offsets = [(-4, -4), (4, -4), (-4, 4), (4, 4)]
        for p in self.players:
            if p.bankrupt:
                continue
            row, col = grid_pos(p.pos)
            cx = ox + col * cell + cell // 2
            cy = oy + row * cell + cell // 2
            dx, dy = offsets[p.idx]
            tx, ty2 = cx + dx, cy + dy
            lcd.ellipse(tx, ty2, 4, 4, TOKEN_OUTLINE, True)
            lcd.ellipse(tx, ty2, 3, 3, PLAYER_COLORS[p.idx], True)

    def hint_for_state(self):
        if self.state == "TURN_START":
            return "A:roll X:bld Y:props"
        if self.state == "JAIL_CHOICE":
            p = self.current()
            if p.gojf_chance or p.gojf_chest:
                return "A:pay B:dbls X:GOJF"
            return "A:pay$50 B:try dbls"
        if self.state == "BUY_PROMPT":
            return "A:buy  B:skip"
        if self.state == "TURN_END":
            return "A/B: continue"
        if self.state == "GAME_OVER":
            return "Thanks for playing!"
        return ""

    def draw_menu(self):
        if self.state == "PORTFOLIO":
            self.draw_portfolio_detail()
            return

        lcd = self.lcd
        p = self.current()
        title = "Build Houses"
        lcd.text(title, 4, 4, WHITE)
        lcd.text("Cash: ${}".format(p.cash), 4, 16, GRAY)

        if not self.menu_items:
            lcd.text("(nothing to show)", 4, 40, GRAY)
        else:
            y = 32
            for n, i in enumerate(self.menu_items):
                tile = TILES[i]
                marker = ">" if n == self.menu_sel else " "
                h = HOUSES[i]
                label = "hotel" if h == 5 else "{} house".format(h)
                line = "{}{} [{}]".format(marker, tile["name"][:16], label)
                color = WHITE if n == self.menu_sel else GRAY
                lcd.text(line[:30], 4, y, color)
                y += 12
                if y > lcd.height - 24:
                    break

        lcd.text("A:build  B/X:back", 4, lcd.height - 10, DKGRAY)

    def draw_portfolio_detail(self):
        """Full stats for whichever property is currently selected -- press
        up/down to move through your properties and see each one's rent,
        cost, and mortgage info instead of just a name in a list."""
        lcd = self.lcd
        p = self.current()
        lcd.text("Portfolio", 4, 4, WHITE)
        lcd.text("Cash: ${}".format(p.cash), 4, 16, GRAY)

        if not self.menu_items:
            lcd.text("(no properties owned)", 4, 40, GRAY)
            lcd.text("B/Y: back", 4, lcd.height - 10, DKGRAY)
            return

        i = self.menu_items[self.menu_sel]
        tile = TILES[i]
        ttype = tile["type"]

        lcd.text("{}/{}".format(self.menu_sel + 1, len(self.menu_items)), 4, 28, DKGRAY)
        for n, line in enumerate(wrap_text(tile["name"], 26)):
            lcd.text(line, 4, 38 + n * 10, WHITE)

        y = 38 + len(wrap_text(tile["name"], 26)) * 10 + 4
        mortgage_val = tile["price"] // 2

        if ttype == "property":
            lcd.text("Group: {}".format(tile["group"]), 4, y, GRAY); y += 10
            lcd.text("Price ${}  Mort ${}".format(tile["price"], mortgage_val), 4, y, GRAY); y += 10
            h = HOUSES[i]
            built = "Hotel" if h == 5 else "{} house(s)".format(h)
            lcd.text("Built: {}".format(built), 4, y, GRAY); y += 10
            monopoly = owns_full_group(p.idx, tile["group"])
            rent = tile["rent"][h] * (2 if (h == 0 and monopoly) else 1)
            lcd.text("Current rent: ${}".format(rent), 4, y, WHITE); y += 10
            lcd.text("House cost: ${}".format(tile["house_cost"]), 4, y, GRAY); y += 10

        elif ttype == "railroad":
            lcd.text("Type: Railroad", 4, y, GRAY); y += 10
            lcd.text("Price ${}  Mort ${}".format(tile["price"], mortgage_val), 4, y, GRAY); y += 10
            count = sum(1 for j, t in enumerate(TILES)
                        if t["type"] == "railroad" and OWNER[j] == p.idx)
            rr_rent = [25, 50, 100, 200]
            lcd.text("Railroads owned: {}".format(count), 4, y, GRAY); y += 10
            lcd.text("Current rent: ${}".format(rr_rent[count - 1] if count else 0), 4, y, WHITE); y += 10

        elif ttype == "utility":
            lcd.text("Type: Utility", 4, y, GRAY); y += 10
            lcd.text("Price ${}  Mort ${}".format(tile["price"], mortgage_val), 4, y, GRAY); y += 10
            count = sum(1 for j, t in enumerate(TILES)
                        if t["type"] == "utility" and OWNER[j] == p.idx)
            mult = 10 if count >= 2 else 4
            lcd.text("Utilities owned: {}".format(count), 4, y, GRAY); y += 10
            lcd.text("Rent: {}x dice roll".format(mult), 4, y, WHITE); y += 10

        status = "MORTGAGED" if MORTGAGED[i] else "Active"
        lcd.text("Status: {}".format(status), 4, y, REDC if MORTGAGED[i] else GREENC)

        lcd.text("U/D:switch  B/Y:back", 4, lcd.height - 10, DKGRAY)


def new_game(lcd, ctrl, num_humans, slot):
    players = [Player(i, i >= num_humans) for i in range(NUM_PLAYERS)]
    build_decks()
    game = Game(lcd, ctrl, players)
    game.save_slot = slot
    game.start_turn()
    return game


# ----------------------------------------------------------------------------
# Setup / save-prompt screens
# ----------------------------------------------------------------------------
def setup_num_humans(lcd, ctrl):
    """Local 'pass the Pico around' multiplayer setup: pick how many seats
    at the table are human (1-4); the rest are computer players."""
    n = 1
    while True:
        lcd.fill(BLACK)
        lcd.text("MONOPOLY", lcd.width // 2 - 34, 40, WHITE)
        lcd.text("Passing the Pico around?", 10, 90, GRAY)
        lcd.text("Human players: {}".format(n), lcd.width // 2 - 52, 110, WHITE)
        lcd.text("U/D: change   A: confirm", 10, 150, DKGRAY)
        lcd.show()

        keys = ctrl.pressed()
        if keys.get("up"):
            n = min(4, n + 1)
        elif keys.get("down"):
            n = max(1, n - 1)
        elif keys.get("a"):
            return n
        time.sleep_ms(30)


def choose_save_slot(lcd, ctrl):
    """Lets you pick from a handful of independent save slots."""
    sel = 0
    while True:
        lcd.fill(BLACK)
        lcd.text("MONOPOLY - Save Slots", 6, 10, WHITE)
        y = 30
        for s in range(NUM_SAVE_SLOTS):
            marker = ">" if s == sel else " "
            status = "Saved game" if save_file_exists(s) else "Empty"
            color = WHITE if s == sel else GRAY
            lcd.text("{}Slot {}: {}".format(marker, s + 1, status), 10, y, color)
            y += 14
        lcd.text("U/D: select  A: choose", 10, y + 10, DKGRAY)
        lcd.text("X: delete save", 10, y + 22, DKGRAY)
        lcd.show()

        keys = ctrl.pressed()
        if keys.get("up"):
            sel = (sel - 1) % NUM_SAVE_SLOTS
        elif keys.get("down"):
            sel = (sel + 1) % NUM_SAVE_SLOTS
        elif keys.get("x"):
            delete_save(sel)
        elif keys.get("a"):
            return sel
        time.sleep_ms(30)


def prompt_continue_save(lcd, ctrl):
    """Returns True to continue the saved game, False to start fresh."""
    while True:
        lcd.fill(BLACK)
        lcd.text("Saved game found!", 20, 90, WHITE)
        lcd.text("A: Continue", 20, 110, GRAY)
        lcd.text("B: New Game", 20, 122, GRAY)
        lcd.show()

        keys = ctrl.pressed()
        if keys.get("a"):
            return True
        if keys.get("b"):
            return False
        time.sleep_ms(30)


# ----------------------------------------------------------------------------
# Wireless multiplayer (ESP-NOW) -- only used if WIRELESS is True.
#
# Protocol: every message's first byte is a type code, so both sides can
# tell packets apart:
#   0 JOIN     client -> host, empty body, "I'd like a seat"
#   1 WELCOME  host -> client, 1 byte: the player index they were assigned
#   2 INPUT    client -> host, 1 byte player idx + 2 bytes button bitmap
#   3 STATE    host -> client, the full compact game state (see encode_state)
#
# This is inherently the least testable part of this file without real
# hardware in hand -- treat it as a solid starting point rather than a
# guaranteed-working implementation. The exact espnow API (recv/irecv,
# timeout handling, add_peer behavior) has varied across MicroPython
# releases, so you may need small tweaks for your firmware version.
# ----------------------------------------------------------------------------
MSG_JOIN = 0
MSG_WELCOME = 1
MSG_INPUT = 2
MSG_STATE = 3

BROADCAST_MAC = b'\xff\xff\xff\xff\xff\xff'
STATE_CODES = {"TURN_START": 0, "TURN_END": 1, "JAIL_CHOICE": 2, "BUY_PROMPT": 3,
               "GAME_OVER": 4, "BUILD_MENU": 5, "PORTFOLIO": 6}
STATE_NAMES = {v: k for k, v in STATE_CODES.items()}
MSG_TEXT_LEN = 20


def _pack_flags(p):
    f = 0
    if p.in_jail: f |= 0x01
    if p.bankrupt: f |= 0x02
    if p.is_bot: f |= 0x04
    gojf_count = (1 if p.gojf_chance else 0) + (1 if p.gojf_chest else 0)
    f |= (min(p.jail_turns, 3) & 0x03) << 3
    f |= (gojf_count & 0x03) << 5
    return f


def _unpack_flags(f):
    return {
        "in_jail": bool(f & 0x01), "bankrupt": bool(f & 0x02), "is_bot": bool(f & 0x04),
        "jail_turns": (f >> 3) & 0x03, "gojf_cards": (f >> 5) & 0x03,
    }


def encode_state(game):
    import struct
    header = struct.pack("<BBBBB", game.turn, game.doubles_count,
                          STATE_CODES.get(game.state, 0), game.dice[0], game.dice[1])
    players_bytes = b""
    for i in range(NUM_PLAYERS):
        if i < len(game.players):
            p = game.players[i]
            players_bytes += struct.pack("<HBB", min(p.cash, 65535), p.pos, _pack_flags(p))
        else:
            players_bytes += struct.pack("<HBB", 0, 0, 0)
    tiles = bytearray(40)
    for i in range(40):
        owner = OWNER[i]
        ov = 0 if owner is None else owner + 1
        tiles[i] = (ov & 0x7) | ((HOUSES[i] & 0x7) << 3) | (0x40 if MORTGAGED[i] else 0)
    msg_text = " | ".join(game.msg)[:MSG_TEXT_LEN]
    msg_bytes = msg_text.encode("utf-8")
    msg_bytes = msg_bytes + b" " * (MSG_TEXT_LEN - len(msg_bytes))
    return bytes([MSG_STATE]) + header + players_bytes + bytes(tiles) + msg_bytes


def decode_state(payload):
    import struct
    body = payload[1:]
    turn, doubles, state_code, d1, d2 = struct.unpack("<BBBBB", body[0:5])
    offset = 5
    players = []
    for i in range(NUM_PLAYERS):
        cash, pos, flags = struct.unpack("<HBB", body[offset:offset + 4])
        offset += 4
        fd = _unpack_flags(flags)
        fd["idx"] = i
        fd["cash"] = cash
        fd["pos"] = pos
        players.append(fd)
    tiles = body[offset:offset + 40]
    offset += 40
    owner = [None] * 40
    houses = [0] * 40
    mortgaged = [False] * 40
    for i in range(40):
        b = tiles[i]
        ov = b & 0x7
        owner[i] = None if ov == 0 else ov - 1
        houses[i] = (b >> 3) & 0x7
        mortgaged[i] = bool(b & 0x40)
    msg_bytes = body[offset:offset + MSG_TEXT_LEN]
    msg_text = msg_bytes.decode("utf-8").rstrip()
    return {
        "turn": turn, "doubles": doubles, "state": STATE_NAMES.get(state_code, "TURN_START"),
        "dice": (d1, d2), "players": players, "owner": owner, "houses": houses,
        "mortgaged": mortgaged, "msg": msg_text,
    }


def draw_remote_board(lcd, state):
    """Standalone renderer used by wireless CLIENTs -- draws whatever state
    the host last broadcast, without running any game logic locally."""
    lcd.fill(BLACK)
    cell = 21
    size = cell * 11
    ox = (lcd.width - size) // 2
    oy = (lcd.height - size) // 2

    for i, tile in enumerate(TILES):
        row, col = grid_pos(i)
        x = ox + col * cell
        y = oy + row * cell
        ttype = tile["type"]
        color = tile_bg_color(tile)
        owner = state["owner"][i]
        lcd.fill_rect(x, y, cell - 1, cell - 1, color)
        if owner is not None:
            draw_owner_marker(lcd, x, y, cell, owner)
        if ttype != "property":
            draw_tile_icon(lcd, x, y, cell, tile)

    px, py = ox + cell, oy + cell
    pw = size - 2 * cell
    ph = size - 2 * cell
    lcd.fill_rect(px, py, pw, ph, BLACK)

    char_w = (pw - 6) // 8
    for n, line in enumerate(wrap_text(state["msg"], char_w)[:3]):
        lcd.text(line, px + 3, py + 3 + n * 10, WHITE)

    ty = py + 3 + 3 * 10 + 4
    for pd in state["players"]:
        status = "BR" if pd["bankrupt"] else "${}".format(pd["cash"])
        marker = ">" if pd["idx"] == state["turn"] else " "
        lcd.text("{}You/{}: {}".format(marker, PLAYER_NAMES[pd["idx"]], status),
                  px + 3, ty, PLAYER_COLORS[pd["idx"]])
        ty += 10

    lcd.text("(watching host's game)", px + 3, py + ph - 10, DKGRAY)

    for pd in state["players"]:
        if pd["bankrupt"]:
            continue
        row, col = grid_pos(pd["pos"])
        cx = ox + col * cell + cell // 2
        cy = oy + row * cell + cell // 2
        idx = pd["idx"]
        offsets = [(-4, -4), (4, -4), (-4, 4), (4, 4)]
        dx, dy = offsets[idx]
        lcd.ellipse(cx + dx, cy + dy, 4, 4, TOKEN_OUTLINE, True)
        lcd.ellipse(cx + dx, cy + dy, 3, 3, PLAYER_COLORS[idx], True)

    lcd.show()


class WirelessHost:
    """Runs on the board that owns the real game. Accepts joins from client
    Picos, routes their button presses into the game, and periodically
    broadcasts the compact game state to everyone."""

    def __init__(self, num_slots):
        import network
        import espnow
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        self.esp = espnow.ESPNow()
        self.esp.active(True)
        self.player_mac = {}      # player idx -> mac bytes
        self.pending_input = {}   # player idx -> keys dict (consumed once)
        self.num_slots = num_slots

    def is_remote(self, idx):
        return idx in self.player_mac

    def get_input(self, idx):
        return self.pending_input.pop(idx, None)

    def poll_joins_and_input(self, game):
        try:
            while True:
                mac, msg = self.esp.recv(0)
                if mac is None or msg is None:
                    break
                mtype = msg[0]
                if mtype == MSG_JOIN:
                    if mac not in self.player_mac.values():
                        target = None
                        for i, p in enumerate(game.players):
                            if p.is_bot and i not in self.player_mac:
                                target = i
                                break
                        if target is not None:
                            try:
                                self.esp.add_peer(mac)
                            except OSError:
                                pass
                            game.players[target].is_bot = False
                            self.player_mac[target] = mac
                            try:
                                self.esp.send(mac, bytes([MSG_WELCOME, target]))
                            except OSError:
                                pass
                elif mtype == MSG_INPUT:
                    idx = msg[1]
                    if self.player_mac.get(idx) == mac:
                        import struct
                        bm = struct.unpack("<H", msg[2:4])[0]
                        self.pending_input[idx] = unpack_buttons(bm)
        except OSError:
            pass  # no data waiting

    def broadcast_state(self, game):
        payload = encode_state(game)
        for mac in self.player_mac.values():
            try:
                self.esp.send(mac, payload)
            except OSError:
                pass


class WirelessClient:
    """Runs on a remote display-only Pico. Joins a host, forwards button
    presses, and renders whatever state the host broadcasts."""

    def __init__(self):
        import network
        import espnow
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        self.esp = espnow.ESPNow()
        self.esp.active(True)
        try:
            self.esp.add_peer(BROADCAST_MAC)
        except OSError:
            pass
        self.host_mac = None
        self.my_idx = None

    def try_join(self, lcd, timeout_ms=15000):
        start = time.ticks_ms()
        while self.host_mac is None:
            try:
                self.esp.send(BROADCAST_MAC, bytes([MSG_JOIN]))
            except OSError:
                pass

            lcd.fill(BLACK)
            lcd.text("Joining host...", 30, 110, WHITE)
            lcd.show()

            deadline = time.ticks_add(time.ticks_ms(), 500)
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                try:
                    mac, msg = self.esp.recv(50)
                except OSError:
                    mac, msg = None, None
                if mac and msg and msg[0] == MSG_WELCOME:
                    self.host_mac = mac
                    self.my_idx = msg[1]
                    try:
                        self.esp.add_peer(mac)
                    except OSError:
                        pass
                    return True

            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                return False
        return True

    def send_input(self, keys):
        if self.host_mac is None or self.my_idx is None:
            return
        if not any(keys.values()):
            return
        import struct
        payload = bytes([MSG_INPUT, self.my_idx]) + struct.pack("<H", pack_buttons(keys))
        try:
            self.esp.send(self.host_mac, payload)
        except OSError:
            pass

    def poll_state(self):
        try:
            mac, msg = self.esp.recv(0)
        except OSError:
            return None
        if mac and msg and msg[0] == MSG_STATE:
            return decode_state(msg)
        return None


def run_wireless_client(lcd, ctrl):
    link = WirelessClient()
    if not link.try_join(lcd):
        lcd.fill(BLACK)
        lcd.text("Could not find host.", 10, 110, WHITE)
        lcd.text("Check WIRELESS host", 10, 122, GRAY)
        lcd.text("is running & in range", 10, 134, GRAY)
        lcd.show()
        return

    state = None
    while True:
        new_state = link.poll_state()
        if new_state:
            state = new_state
        keys = ctrl.pressed()
        link.send_input(keys)
        if state:
            draw_remote_board(lcd, state)
        time.sleep_ms(30)


# ----------------------------------------------------------------------------
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

    if WIRELESS and WIRELESS_ROLE == "client":
        run_wireless_client(lcd, ctrl)
        return

    slot = choose_save_slot(lcd, ctrl)
    if save_file_exists(slot) and prompt_continue_save(lcd, ctrl):
        game = load_game(lcd, ctrl, slot)
    else:
        delete_save(slot)
        num_humans = setup_num_humans(lcd, ctrl)
        game = new_game(lcd, ctrl, num_humans, slot)

    wireless = None
    if WIRELESS and WIRELESS_ROLE == "host":
        wireless = WirelessHost(NUM_PLAYERS)

    game.draw()

    while True:
        if wireless:
            wireless.poll_joins_and_input(game)

        keys = ctrl.pressed()
        if game.state != "GAME_OVER":
            p = game.current()
            if p.is_bot:
                game.bot_take_turn()
            elif wireless and wireless.is_remote(p.idx):
                rkeys = wireless.get_input(p.idx)
                if rkeys:
                    game.handle_input(rkeys)
            else:
                game.handle_input(keys)
        else:
            game.handle_input(keys)

        game.draw()

        if wireless:
            wireless.broadcast_state(game)

        time.sleep_ms(30)


if __name__ == "__main__":
    main()