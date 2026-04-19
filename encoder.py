from machine import Pin, I2C
from i2c_encoder import AdafruitEncoder
from time import sleep

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
encoder = AdafruitEncoder(i2c)

while True:
    print("Position:", encoder.get_delta(), "Button pressed:", encoder.get_switch())
    sleep(.1)
