from machine import Pin, I2C
from time import sleep
from pcf8574 import PCF8574
from ky040 import KY040_PCF
from SSD1306 import SSD1306_I2C
from i2c_encoder import AdafruitEncoder
i2c = I2C(1, scl = 15, sda = 14)
oled = SSD1306_I2C(128, 64, i2c, addr=0x3D)
pcf = PCF8574(i2c, 0x20)
yellow = 0
blue = 1
red = 2
green = 3
sw = 4
clk = 5
dt = 6
encoder = AdafruitEncoder(i2c)
pos = 0
while True:
    delta = encoder.get_delta()
    if delta != 0:
        pos -= delta
        print("Pos:", pos)
    
    if encoder.get_switch() == 0:
        print("button pressed")
    
    sleep(0.2)

while True:
    data = encoder._read_reg(0x11, 0x30, 4)
    pos = int.from_bytes(data, 'big')
    if pos & 0x80000000:
        pos = pos - 0x100000000
    print(f"raw={[hex(b) for b in data]} pos={pos}")
    sleep(0.2)
while True:
    data = encoder._read_reg(0x11, 0x30, 4)
    print(f"pos register: {[b for b in data]}")
    sleep(0.2)
def find_encoder_register(i2c):
    # capture baseline
    baseline = {}
    for module in range(0x00, 0x20):
        for reg in range(0x00, 0x80):
            try:
                i2c.writeto(0x36, bytes([module, reg]))
                data = i2c.readfrom(0x36, 4)
                baseline[(module, reg)] = list(data)
            except:
                pass
    print("baseline captured, turn the knob")

    # keep scanning until we find a change
    while True:
        for module in range(0x00, 0x20):
            for reg in range(0x00, 0x80):
                try:
                    i2c.writeto(0x36, bytes([module, reg]))
                    data = list(i2c.readfrom(0x36, 4))
                    if (module, reg) in baseline and data != baseline[(module, reg)]:
                        print(f"CHANGED module={hex(module)} reg={hex(reg)}: {[hex(b) for b in baseline[(module,reg)]]} -> {[hex(b) for b in data]}")
                        baseline[(module, reg)] = data  # update baseline
                except:
                    pass

find_encoder_register(i2c)
"""
while True:
    delta = encoder.get_delta()
    if delta != 0:
        print(f"delta={delta} pos={encoder._last_pos}")
    if encoder.get_switch() == 0:
        print("button pressed")
    sleep(.01)

while True:
    pos = encoder.read()
    btn = encoder.get_switch()
    print(f"Yellow: {not pcf.pin(yellow)}, Blue: {not pcf.pin(blue)}, Red: {not pcf.pin(red)}, Green: {not pcf.pin(green)}, Rotary Pos: {int(pos/2)}, Rotary Button: {not btn}\n\n\n\n\n")
    sleep(0.01)
"""