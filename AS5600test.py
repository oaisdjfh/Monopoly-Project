from machine import I2C, Pin
from as5600 import AS5600
from time import sleep
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)
sensor = AS5600(i2c)
while True:
    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
    if sensor.is_magnet_detected():
        print(f"Angle: {sensor.angle}°")
        print(f"Abs Angle: {sensor.absolute_angle}°")
    else:
        print(f"No magnet detected")
    sleep(0.5)