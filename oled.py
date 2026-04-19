from machine import Pin, I2C
from SSD1306 import SSD1306_I2C
i2c = I2C(0,sda=Pin(0), scl=Pin(1))
print("I2C devices found:", i2c.scan())
oled = SSD1306_I2C(128, 128, i2c, addr = 0x3D)
oled.text("test", 0, 0, 1)
oled.show()