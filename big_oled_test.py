from Big_SSD1306 import SSD1327
# ── Quick self-test ────────────────────────────────────────────────────────────

def demo(i2c):
    """
    Run a short demo sequence.  Call with a configured I2C object, e.g.:

        from machine import I2C, Pin
        i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400_000)
        from ssd1327 import demo
        demo(i2c)
    """
    import utime

    oled = SSD1327(i2c)

    # Gradient background
    oled.gradient_fill(0, 0, 128, 128, 0, 8)
    oled.show()
    utime.sleep_ms(500)

    # Bordered frame
    oled.rect_outline(4, 4, 120, 120, 15)
    oled.show()
    utime.sleep_ms(500)

    # Circles
    oled.circle(64, 64, 40, 15)
    oled.fill_circle(64, 64, 10, 10)
    oled.show()
    utime.sleep_ms(500)

    # Text
    oled.text("SSD1327", 30, 56, 15)
    oled.text("128x128", 30, 66, 8)
    oled.show()
    utime.sleep_ms(2000)

    # Invert
    oled.invert(True)
    utime.sleep_ms(800)
    oled.invert(False)
    utime.sleep_ms(500)

    # Contrast sweep
    for c in list(range(0, 256, 16)) + list(range(255, 63, -16)):
        oled.contrast(c)
        utime.sleep_ms(30)

    oled.contrast(0x7F)
    print("Demo complete.")
    return oled