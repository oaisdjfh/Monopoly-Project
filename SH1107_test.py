from SH1107 import SH1107
from machine import I2C, Pin, SoftI2C
import time, random
# ── Quick demo ─────────────────────────────────────────────────────────────────
#i2c = I2C(1, scl=Pin(15), sda=Pin(14))
i2c = SoftI2C(scl=Pin(15), sda=Pin(14), freq=400000)
oled = SH1107(i2c, rotation = 270)

def roll_dice(x=30, y=30, w=60, h=60, loops=1):
    for _ in range(loops):
        for i in range(16):
            if i == 2:
                continue
            oled.fill(0)
            oled.draw_image("frame_{:02d}.img".format(i), x, y, w, h)
            oled.show()
    oled.fill(0)
    oled.text_scaled(str(random.randint(1, 6)), x+10, y+5, 60)
    oled.show()

oled.fill(0)
oled.show()
def demo(i2c):
    
    oled.fill(0)
    oled.draw_image("IMG_1948.img", 0, 0, 128, 128)
    oled.show()
    """
    Run a short visual demo.

        from machine import I2C, Pin
        from sh1107 import demo
        demo(I2C(0, scl=Pin(22), sda=Pin(21), freq=400_000))
    
    import utime

    oled = SH1107(i2c)

    # Clear + border
    oled.fill(0)
    oled.rect(0, 0, 128, 128, 1)
    oled.show()
    utime.sleep_ms(400)

    # Circles
    oled.fill_circle(64, 64, 30, 1)
    oled.circle(64, 64, 45, 1)
    oled.show()
    utime.sleep_ms(600)

    # Text overlay
    oled.fill_rect(20, 55, 88, 18, 0)
    oled.text("SH1107", 34, 57, 1)
    oled.text("128x128", 30, 66, 1)
    oled.show()
    utime.sleep_ms(1500)

    # Invert flash
    for _ in range(3):
        oled.invert(True);  utime.sleep_ms(200)
        oled.invert(False); utime.sleep_ms(200)

    # Contrast sweep
    for c in list(range(0, 256, 8)) + list(range(255, 0x6F, -8)):
        oled.contrast(c)
        utime.sleep_ms(15)
    oled.contrast(0x7F)

    print("SH1107 demo complete.")
    return oled
    """
