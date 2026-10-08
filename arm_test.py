from pcf8574 import PCF8574

from SSD1306 import SSD1306_I2C
from machine import I2C, Pin, SoftI2C
from time import sleep
from as5600 import AS5600
from i2c_encoder import AdafruitEncoder
# Initialize I2C on the Raspberry Pi Pico
i2c_control = SoftI2C(scl=Pin(15), sda=Pin(14))

pcf = PCF8574(i2c_control, 0x20)
#oled = SSD1306_I2C(128, 64, i2c_control, addr=0x3D)
yellow = 4
blue = 1
red = 2
green = 3
sw = 4
clk = 5
dt = 6
magnet_value = 0
#encoder = KY040_PCF(pcf, pin_clk_gpio=13, pin_dt_pcf=dt, pin_sw=sw)
#encoder = AdafruitEncoder(i2c_control)
extend_pos = True
limit_switch = Pin(3, Pin.IN, Pin.PULL_UP)
extend_motor_1 = Pin(7, Pin.OUT)
extend_motor_2 = Pin(8, Pin.OUT)
rotation_i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
#i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
ir_sensor = Pin(9, Pin.IN, Pin.PULL_DOWN)
rotation_sensor = AS5600(rotation_i2c)
magnet = Pin(5, Pin.OUT, Pin.PULL_DOWN)
base_stepper = 0
microstep = 800
base_dir = Pin(21, Pin.OUT)
base_pul = Pin(20, Pin.OUT)
degree = 0
rotation_sensor.set_origin(45.0, auto = True)
def deepcopy(arr):
    new_arr = []
    for i in range(len(arr)):
        new_arr.append(arr[i])
    return new_arr
def zero(DIR_PIN, PUL_PIN, use_ir=False):

    if use_ir:
        for i in range(720):
            print(ir_sensor.value())
            if ir_sensor.value() == 0:
                #step_motor(move_degree, 1, 0.005, DIR_PIN, PUL_PIN)
                rotation_sensor.set_origin(45.0)
                print("zeroed")
                return 45
            else:
                move_degree = .5
                move_degree = int((microstep*move_degree)/360)
                step_motor(move_degree, 0, 0.006, DIR_PIN, PUL_PIN)
            sleep(.5)
    else:
        direction = 1
        if rotation_sensor.angle >180:
            direction = 0
        while True:
            if abs(rotation_sensor.angle) < 2:
                #step_motor(move_degree, direction, 0.005, DIR_PIN, PUL_PIN)
                rotation_sensor.set_origin(0.0)
                print("zeroed")
                return 0
            else:
                move_degree = .5
                move_degree = int((microstep*move_degree)/360)
                step_motor(move_degree, direction, 0.005, DIR_PIN, PUL_PIN)
    print("failed to zero")
    return degree
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
def draw_degree(fb, x, y):
    fb.pixel(x, y, 1)
    fb.pixel(x+1, y, 1)
    fb.pixel(x+2, y, 1)
    fb.pixel(x, y+1, 1)
    fb.pixel(x+2, y+1, 1)
    fb.pixel(x, y+2, 1)
    fb.pixel(x+1, y+2, 1)
    fb.pixel(x+2, y+2, 1)
places = [
          [0,0],[1,11],[2,18],[3,28],[4,36],[5,45],[6,54],[7,64],[8,72],[9,79], #0 is GO
          [10,90], [11,100],[12,107],[13,116],[14,124],[15,135],[16,145],[17,153],[18,162],[19,168], #10 is jail
          [20,180],[21,192],[22,199],[23,207],[24,216],[25,225],[26,234],[27,244],[28,251],[29,258],#20 is free parking
          [30,270],[31,281],[32,289],[33,298],[34,306],[35,315],[36,325],[37,334],[38,343],[39,349]#30 is go to jail
          ]
while True:
    long = int(input("magnet, control arm, extension change, extension control, long, steps, reset degree, print info, zero, place, manual (10/9/8/7/6/5/4/3/2/1/0): "))
    if long == 11:
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
            
    if long == 10:
        magnet.value(not magnet_value)
        magnet_value = not magnet_value
        print("Magnet value:" + str(magnet.value()))
    if long == 9:
        #last_encoder_pos = encoder.read()
        arm_manual = True
        oled.text("Manual mode", 0, 6)
        oled.text("Arm extension ?", 0, 26)
        oled.show()
        while True:
            oled.rect(0, 36, 130, 50, 0, True)
            oled.text("Arm at " + str(round(rotation_sensor.angle)) , 0, 36)
            draw_degree(oled, 60+8*len(str(round(rotation_sensor.angle))), 36)
            oled.show()
            #encoder.read()
            if pcf.pin(blue) == 0:
                arm_manual = not arm_manual
                if arm_manual:
                    
                    oled.text("Place mode", 0, 6, 0)
                    oled.text("Manual mode", 0, 6)
                else:
                    oled.text("Manual mode", 0, 6, 0)
                    oled.text("Place mode", 0, 6)
                oled.show()
                sleep(.3)
            if pcf.pin(green) == 0:
                degree = zero(base_dir, base_pul, use_ir=True)

            if pcf.pin(red) == 0:
                oled.text("magnet off", 0, 16, 0)
                oled.text("magnet on", 0, 16)
                oled.show()
                magnet.high()
            else:
                magnet.low()
                oled.text("magnet on", 0, 16, 0)
                oled.text("magnet off", 0, 16)
                oled.show()

            if pcf.pin(yellow) == 0:
                if limit_switch.value() == 1:
                    extend_motor_1.high()
                    extend_motor_2.low()
                    sleep(7.5)
                    extend_motor_1.high()
                    extend_motor_2.high()
                    oled.text("Arm extension ?", 0, 26, 0)
                    oled.text("arm retracted", 0, 26, 0)
                    oled.text("arm extened", 0, 26)
                    oled.show()
                else:
                    while True:
                        extend_motor_1.low()
                        extend_motor_2.high()
                        sleep(.1)
                        extend_motor_1.high()
                        extend_motor_2.high()
                        #encoder.read()
                        if limit_switch.value() == 1:
                            break
                    oled.text("Arm extension ?", 0, 26, 0)
                    oled.text("arm extened", 0, 26, 0)
                    oled.text("arm retracted", 0, 26)
                    oled.show()
                sleep(.3)

            delta = encoder.get_delta()
            
            if delta != 0:
                if arm_manual:
                    move_degree = 5
                    move_degree = int((microstep * move_degree) / 360)
                    if delta < 0:
                        step_motor(move_degree, 1, 0.007, base_dir, base_pul)
                    else:
                        step_motor(move_degree, 0, 0.007, base_dir, base_pul)
                else:
                    temp_place = 0
                    while True:
                        oled.rect(0, 36, 130, 10, 0, True)
                        oled.text("Place: " + str(temp_place), 0, 36)
                        oled.show()
                        temp_place -= encoder.get_delta()
                        if temp_place < 0:
                            temp_place = 39
                        if temp_place > 39:
                            temp_place = 0
                        if pcf.pin(blue) == 0:
                            oled.text("Place mode", 0, 6, 0)
                            oled.text("Manual mode", 0, 6)
                            oled.show()
                            arm_manual = not arm_manual
                            sleep(.3)
                            break
                        if encoder.get_switch() == 0:
                            degree = round(rotation_sensor.angle)
                            place = temp_place
                            if places[place][1]<degree:
                                move_degree = 360-degree+places[place][1]
                            else:
                                move_degree = places[place][1]-degree
                            degree = places[place][1]
                            magnet.value(1)
                            if move_degree > 180 or move_degree < 0:
                                direction = 1
                            else:
                                direction = 0
                            direction = 0
                            move_degree = abs(move_degree)
                            move_degree = int((microstep*move_degree)/360)
                            step_motor(move_degree, direction, .02, base_dir, base_pul)
                            while True:
                                if abs(degree-rotation_sensor.angle) > 2:
                                    print("Misalignment detected. Adjusting...")
                                    current = rotation_sensor.angle

                                    if current < 0:
                                        current += 360


                                    move_degree = (degree - current + 540) % 360 - 180

                                    distance = abs(move_degree)

                                    if move_degree > 0:
                                        direction = 0   # counter-clockwise
                                    else:
                                        direction = 1   # clockwise
                                    print(current, degree, rotation_sensor.angle, move_degree, direction)
                                    if abs(move_degree) < 2:
                                        print("Alignment complete.")
                                        break
                                    move_degree = int((microstep*abs(move_degree))/360)
                                    
                                    step_motor(move_degree, direction, .02, base_dir, base_pul)
                                else:
                                    print("Alignment complete.")
                                    break
                            break

            if encoder.get_switch() == 0:
                oled.fill(0)
                oled.show()
                break
            sleep(.01)
    if long == 8:
        if limit_switch.value() == 1:
            extend_motor_1.high()
            extend_motor_2.low()
            sleep(5.5)
            extend_motor_1.high()
            extend_motor_2.high()
        else:
            while True:
                extend_motor_1.low()
                extend_motor_2.high()
                sleep(.1)
                extend_motor_1.high()
                extend_motor_2.high()
                if limit_switch.value() == 1:
                    break

    if long == 7:
        time = float(input("Time: "))
        if int(input("Extend or retract? (0 for extend, 1 for retract): ")):
            extend_motor_1.low()
            extend_motor_2.high()
            sleep(time)
            extend_motor_1.low()
            extend_motor_2.low()
        else:
            extend_motor_1.high()
            extend_motor_2.low()
            sleep(time)
            extend_motor_1.low()
            extend_motor_2.low()


    if long == 6:
        move_degree = float(input("Degrees: "))
        direction_in = (input("Dir(CW, CCW): "))
        speed = float(input("Speed(1-0.005): "))
        
        direction = 1
        if direction_in == "CW":
            direction = 0
        degree += move_degree - 2*move_degree*direction
        move_degree = int((microstep*move_degree)/360)
        speed = 1.005-speed
        while True:
            step_motor(move_degree, direction, speed, base_dir, base_pul)
            sleep(0.5)
    if long == 5:
        
        delay = float(input("Delay: "))
        while True:
            dir = int(input("Direction(0 for CW, 1 for CCW): "))
            if dir == 2: break
            step_motor(1,dir, delay, base_dir, base_pul)
    if long == 0:
        magnet.value(1)
        move_degree = float(input("Degrees: "))
        direction_in = (input("Dir(CW, CCW): "))
        speed = float(input("Speed(1-0.005): "))
        
        direction = 1
        if direction_in == "CW":
            direction = 0
        degree += move_degree - 2*move_degree*direction
        move_degree = int((microstep*move_degree)/360)
        speed = 1.005-speed
        step_motor(move_degree, direction, speed, base_dir, base_pul)
        print()
        sleep(0.5)
            
        
    elif long == 2:
        if input("Use IR sensor? (y/n): ") == "y":
            degree = zero(base_dir, base_pul, use_ir=True)
        else:
            degree = zero(base_dir, base_pul)
    elif long == 3:
        print("Limit Switch: ", limit_switch.value())
        print("Degree: ", degree)
        print("Rotation Sensor: ", rotation_sensor.angle)
        print("IR Sensor: ", ir_sensor.value())
        magnet.value(0)
    elif long == 4:
        degree = round(rotation_sensor.angle)
        print("Degree reset to: ", degree)
    elif long == 1:
        degree = round(rotation_sensor.angle)
        place = int(input("Place: "))
        if places[place][1]<degree:
            move_degree = 360-degree+places[place][1]
        else:
            move_degree = places[place][1]-degree
        degree = places[place][1]
        magnet.value(1)
        if move_degree > 180 or move_degree < 0:
            direction = 1
        else:
            direction = 0
        move_degree = abs(move_degree)
        move_degree = int((microstep*move_degree)/360)
        step_motor(move_degree, direction, .02, base_dir, base_pul)
        while True:
            if abs(degree-rotation_sensor.angle) > 2:
                print("Misalignment detected. Adjusting...")
                current = rotation_sensor.angle

                if current < 0:
                    current += 360


                move_degree = (degree - current + 540) % 360 - 180

                distance = abs(move_degree)

                if move_degree > 0:
                    direction = 0   # counter-clockwise
                else:
                    direction = 1   # clockwise
                print(current, degree, rotation_sensor.angle, move_degree, direction)
                if abs(move_degree) < 2:
                    print("Alignment complete.")
                    break
                move_degree = int((microstep*abs(move_degree))/360)
                
                step_motor(move_degree, direction, .02, base_dir, base_pul)
            else:
                print("Alignment complete.")
                break