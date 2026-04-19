"""
example_ST7735.py — Demo for the ST7735 MicroPython driver

Tested on Raspberry Pi Pico (RP2040) with an Adafruit 1.8" 128×160 TFT.
Adjust the Pin numbers to match your wiring.
"""

from machine import SPI, Pin, PWM
import time
import ST7735

# ── Configure SPI & pins ──────────────────────────────────────────────────────
# Raspberry Pi Pico example (SPI0)
spi = SPI(0, baudrate=20_000_000, polarity=0, phase=0,
          sck=Pin(2), mosi=Pin(3))

display = ST7735.ST7735(
    spi,
    cs  = Pin(5, Pin.OUT),
    dc  = Pin(6, Pin.OUT),
    rst = Pin(7, Pin.OUT),
    width=128, height=160,
    rotation=0,           # 0 / 90 / 180 / 270
    bgr=False,            # True for some clone displays
    offset_x=0, offset_y=0
)

# ── For 1.44" 128×128 displays use: ──────────────────────────────────────────
# display = ST7735.ST7735(spi, cs=..., dc=..., rst=...,
#                         width=128, height=128,
#                         offset_x=2, offset_y=3)

# ── Demo scenes ───────────────────────────────────────────────────────────────

def demo_colors():
    """Sweep through solid colour fills."""
    for color in (ST7735.RED, ST7735.GREEN, ST7735.BLUE,
                  ST7735.CYAN, ST7735.MAGENTA, ST7735.YELLOW,
                  ST7735.WHITE, ST7735.BLACK):
        display.fill(color)
        time.sleep_ms(300)

def demo_shapes():
    display.fill(ST7735.BLACK)

    # Rectangles
    display.rect(5, 5, 50, 30, ST7735.WHITE)
    display.fill_rect(60, 5, 50, 30, ST7735.BLUE)

    # Lines
    display.line(0, 0, 127, 159, ST7735.GREEN)
    display.hline(0, 80, 128, ST7735.YELLOW)
    display.vline(64, 0, 160, ST7735.RED)

    # Circles
    display.circle(32, 120, 20, ST7735.CYAN)
    display.fill_circle(96, 120, 20, ST7735.MAGENTA)

    time.sleep_ms(2000)

def demo_text():
    display.fill(ST7735.BLACK)
    display.text("ST7735 Driver", 4,  4, ST7735.WHITE)
    display.text("MicroPython",   4, 20, ST7735.YELLOW)
    display.text("128x160",       4, 36, ST7735.CYAN)
    display.text("Hello!",        4, 60, ST7735.GREEN,  scale=2)
    display.text("RGB565",        4, 90, ST7735.ORANGE, scale=2)
    time.sleep_ms(3000)

def demo_invert():
    display.fill(ST7735.BLACK)
    display.text("Invert test", 10, 70, ST7735.WHITE)
    time.sleep_ms(1000)
    for _ in range(4):
        display.invert(True);  time.sleep_ms(500)
        display.invert(False); time.sleep_ms(500)

# ── Run ───────────────────────────────────────────────────────────────────────


backlight = PWM(Pin(8))
backlight.freq(1000)
brightness = 1
backlight.duty_u16(int(65535*brightness))  # 50% brightness (0–65535)
while True:
    demo_colors()
    demo_shapes()
    demo_text()
    demo_invert()