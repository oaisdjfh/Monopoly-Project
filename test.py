import neopixel
import machine

# setup
NUM_LEDS = 6
DATA_PIN = machine.Pin(0)  # whatever GPIO pin you use
np = neopixel.NeoPixel(DATA_PIN, NUM_LEDS)

# set colors (R, G, B) — values 0-255
np[0] = (255, 0, 0)    # red
np[1] = (0, 255, 0)    # green
np[2] = (0, 0, 255)    # blue
np[3] = (255, 255, 0)  # yellow
np[4] = (0, 255, 255)  # cyan
np[5] = (255, 0, 255)  # magenta

np.write()  # sends all the bits out