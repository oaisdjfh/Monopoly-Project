

from machine import I2C, Pin
import time

# Initialize I2C – use the correct pins for your board
# For Raspberry Pi Pico, default I2C0 uses GP0 (SDA) and GP1 (SCL)


i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)  # Adjust frequency as needed

# You can use I2C(1, scl=Pin(3), sda=Pin(2)) for I2C1 on GP2 and GP3

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
    time.sleep(1)  # wait 5 seconds before scanning again
