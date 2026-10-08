"""
WS2812B Addressable LED Driver for Raspberry Pi Pico
MicroPython

Wiring:
  WS2812B DATA IN  -->  GP0 (or any GPIO pin, change PIN below)
  WS2812B VCC      -->  VBUS (5V) or 3.3V for short strips
  WS2812B GND      -->  GND

The Pico's PIO (Programmable I/O) state machine is used to generate
the precise timing the WS2812B protocol requires.
"""

import array
import time
from machine import Pin
import rp2

# ── Configuration ──────────────────────────────────────────────────────────────
PIN        = 0    # GPIO pin connected to DATA IN
NUM_LEDS   = 50    # Number of LEDs in your strip
BRIGHTNESS = 0.1  # Global brightness (0.0 – 1.0)


# ── PIO State Machine ──────────────────────────────────────────────────────────
# The WS2812B protocol needs very tight timing (~400 ns / ~800 ns pulses).
# The Pico's PIO handles this in hardware so Python timing doesn't matter.

@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    autopull=True,
    pull_thresh=24,
)
def ws2812b_pio():
    # T1 = 2 cycles, T2 = 5 cycles, T3 = 3 cycles  @ 8 MHz → 125 ns/cycle
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)             .side(0) [T3 - 1]   # Pull next bit; line LOW
    jmp(not_x, "do_zero") .side(1) [T1 - 1]   # Line HIGH; branch if bit=0
    jmp("bitloop")        .side(1) [T2 - 1]   # Bit=1: stay HIGH longer
    label("do_zero")
    nop()                 .side(0) [T2 - 1]   # Bit=0: go LOW early
    wrap()


class WS2812B:
    """
    Simple WS2812B / NeoPixel driver using the RP2040 PIO.

    Usage:
        leds = WS2812B(pin=0, num_leds=8, brightness=0.3)
        leds[0] = (255, 0, 0)   # Set LED 0 to red
        leds.show()             # Push to strip
    """

    def __init__(self, pin: int = PIN, num_leds: int = NUM_LEDS,
                 brightness: float = BRIGHTNESS):
        self.num_leds  = num_leds
        self.brightness = max(0.0, min(1.0, brightness))
        # 32-bit buffer per LED (only 24 bits used: GRB order)
        self._buf = array.array("I", [0] * num_leds)

        self._sm = rp2.StateMachine(
            0,
            ws2812b_pio,
            freq=8_000_000,
            sideset_base=Pin(pin),
        )
        self._sm.active(1)

    # ── Buffer helpers ─────────────────────────────────────────────────────────

    def _encode(self, r: int, g: int, b: int) -> int:
        """Apply brightness and pack into GRB word (WS2812B wants GRB)."""
        br = self.brightness
        r = int(r * br) & 0xFF
        g = int(g * br) & 0xFF
        b = int(b * br) & 0xFF
        return (g << 16) | (r << 8) | b

    def __setitem__(self, idx: int, color: tuple):
        """leds[i] = (r, g, b)"""
        r, g, b = color
        self._buf[idx] = self._encode(r, g, b)

    def __getitem__(self, idx: int) -> tuple:
        """Returns (r, g, b) — before brightness scaling."""
        word = self._buf[idx]
        g = (word >> 16) & 0xFF
        r = (word >>  8) & 0xFF
        b =  word        & 0xFF
        return (r, g, b)

    def fill(self, color: tuple):
        """Set every LED to the same color."""
        r, g, b = color
        encoded = self._encode(r, g, b)
        for i in range(self.num_leds):
            self._buf[i] = encoded

    def clear(self):
        """Turn all LEDs off."""
        self.fill((0, 0, 0))
        self.show()

    def show(self):
        """Push the buffer to the strip one word at a time (blocking)."""
        for word in self._buf:
            self._sm.put(word, 8)  # blocks until FIFO has space
        # WS2812B needs >50 µs low to latch; give it 100 µs
        time.sleep_us(100)

    def set_brightness(self, brightness: float):
        """Change global brightness without rewriting individual colours."""
        self.brightness = max(0.0, min(1.0, brightness))


# ── Demo animations ────────────────────────────────────────────────────────────

def demo_solid_colors(leds: WS2812B, delay: float = 0.8):
    """Cycle through solid colours."""
    colors = [
        (255,   0,   0),   # Red
        (0,   255,   0),   # Green
        (0,     0, 255),   # Blue
        (255, 255,   0),   # Yellow
        (0,   255, 255),   # Cyan
        (255,   0, 255),   # Magenta
        (255, 255, 255),   # White
    ]
    for color in colors:
        leds.fill(color)
        leds.show()
        time.sleep(delay)


def demo_rainbow(leds: WS2812B, cycles: int = 2, delay: float = 0.02):
    """Scroll a rainbow across the strip."""
    def wheel(pos: int) -> tuple:
        """0–255 → RGB rainbow."""
        pos = pos & 0xFF
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (0, 255 - pos * 3, pos * 3)
        else:
            pos -= 170
            return (pos * 3, 0, 255 - pos * 3)

    for _ in range(cycles * 256):
        for i in range(leds.num_leds):
            pixel_index = (i * 256 // leds.num_leds)
            leds[i] = wheel(pixel_index)
        leds.show()
        time.sleep(delay)


def demo_chase(leds: WS2812B, color=(255, 80, 0), cycles: int = 5,
               delay: float = 0.08):
    """Single lit pixel chasing around the strip."""
    for _ in range(cycles):
        for i in range(leds.num_leds):
            leds.fill((0, 0, 0))  # zero the buffer only, no show()
            leds[i] = color
            leds[i-1] = color
            leds[i-2] = color
            leds[i-3] = color
            leds.show()
            time.sleep(delay)


def demo_fade(leds: WS2812B, color=(0, 100, 255), steps: int = 60,
              delay: float = 0.02):
    """Breathe / fade in and out."""
    r, g, b = color
    original_brightness = leds.brightness
    for _ in range(2):
        for step in range(steps):
            leds.set_brightness(step / steps)
            leds.fill((r, g, b))
            leds.show()
            time.sleep(delay)
        for step in range(steps, 0, -1):
            leds.set_brightness(step / steps)
            leds.fill((r, g, b))
            leds.show()
            time.sleep(delay)
    leds.set_brightness(original_brightness)

def wheel(pos):
    pos = pos & 0xFF
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)
# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    leds = WS2812B(pin=PIN, num_leds=NUM_LEDS, brightness=BRIGHTNESS)

    print("WS2812B demo — press Ctrl+C to stop")
    try:
        red = 5
        green = 125
        blue = 255
        pos = 0
        while True:
            demo_solid_colors(leds, delay=0.5)
            #demo_chase(leds, color=(pos, 255-pos, pos*2 & 0xFF), cycles=1, delay=0.03)
            pos = (pos + 1) & 0xFF
            time.sleep_ms(20)
    except KeyboardInterrupt:
        leds.clear()
        print("Done.")