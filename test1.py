from machine import Pin
from time import sleep
base_dir = Pin(1, Pin.OUT)
base_pul = Pin(0, Pin.OUT)
def step_motor(steps, direction, delay, DIR_PIN, PUL_PIN):
    """
    Function to move the stepper motor.
    :param steps: Number of steps to move.
    :param direction: Direction (1 for CW, 0 for CCW).
    :param delay: Delay in seconds between steps.
    """
    DIR_PIN.value(direction)  # Set direction
    for _ in range(steps):
        PUL_PIN.high()  # Pulse high
        sleep(delay)
        PUL_PIN.low()  # Pulse low
        sleep(delay)
degree = 0
microstep = 800
move_degree = float(720)
direction_in = ("CW")
speed = float(1)

direction = 1
if direction_in == "CW":
    direction = 0
degree += move_degree - 2*move_degree*direction
move_degree = int((microstep*move_degree)/360)
speed = 1.005-speed
step_motor(move_degree, direction, speed, base_dir, base_pul)
print()
sleep(0.5)