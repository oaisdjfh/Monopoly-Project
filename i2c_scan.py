from machine import I2C, Pin
import time



i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)


def scan_i2c():
    print("Scanning I2C bus...")
    devices = i2c.scan()
    
    if not devices:
        print("No I2C devices found.")
    else:
        print(f"Found {len(devices)} device(s):")
        for device in devices:
            print(f" - I2C address: {hex(device)}")

while True:
    scan_i2c()
    time.sleep(1)
