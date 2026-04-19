from machine import SoftI2C, Pin
from PCA9548A import PCA9548A

i2c = SoftI2C(scl=Pin(17), sda=Pin(16), freq=400000)
print(i2c.scan())
mux = PCA9548A(i2c)

# Scan all channels to find which device is on which channel
results = mux.scan_all()
print(results)

mux.select(0)

from pcf8574 import PCF8574
from time import sleep
pcf = PCF8574(i2c, 0x20)
while True:
    print(pcf.pin(0), pcf.pin(1), pcf.pin(2), pcf.pin(3))
    sleep(.1)
