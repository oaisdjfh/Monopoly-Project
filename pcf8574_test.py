from machine import Pin, SoftI2C
from pcf8574 import PCF8574
from time import sleep

i2c = SoftI2C(scl=Pin(15), sda=Pin(14), freq=400000)
int = Pin(10, Pin.IN, Pin.PULL_DOWN)
pcf = PCF8574(i2c, 0x20, int_pin = int)
pcf.set_interrupt_callback
while True:
    print(pcf.pin(0), pcf.pin(1), pcf.pin(2), pcf.pin(3))
    sleep(.1)
