from pcf8574 import PCF8574
from SSD1306 import SSD1306_I2C
from machine import I2C, Pin, SoftI2C
from time import sleep
from as5600 import AS5600
from i2c_encoder import AdafruitEncoder
from SH1107 import SH1107
from PCA9548A import PCA9548A

controllers_connected = []
id_pin1 = Pin(13, Pin.IN, Pin.PULL_UP)
id_pin4 = Pin(11, Pin.IN, Pin.PULL_UP)
id_pin2 = Pin(10, Pin.IN, Pin.PULL_UP)
id_pin3 = Pin(12, Pin.IN, Pin.PULL_UP)
yellow = 0
blue = 1
red = 2
green = 3
##################################################

if id_pin1.value() == 0:
    controllers_connected.append(1)
    i2c_control1 = SoftI2C(scl=Pin(15), sda=Pin(14), freq = 200000)
    oled_big1 = SH1107(i2c_control1, rotation = 270)
    pcf1 = PCF8574(i2c_control1, 0x20)
    oled1 = SSD1306_I2C(128, 64, i2c_control1, addr=0x3D)
    
    #encoder = KY040_PCF(pcf, pin_clk_gpio=13, pin_dt_pcf=dt, pin_sw=sw)
    encoder1 = AdafruitEncoder(i2c_control1)

##################################################
if id_pin4.value() == 0:
    controllers_connected.append(4)
    mux4 = PCA9548A(i2c_control1)
    mux4.select(1)
    oled_big4 = SH1107(i2c_control1, rotation=270)
    mux4.select(0)
    pcf4 = PCF8574(i2c_control1, 0x20)
    mux4.select(2)
    oled4 = SSD1306_I2C(128, 64, i2c_control1, addr=0x3D)

    #encoder = KY040_PCF(pcf, pin_clk_gpio=13, pin_dt_pcf=dt, pin_sw=sw)
    encoder4 = AdafruitEncoder(i2c_control1)

##################################################
if id_pin2.value() == 0:
    controllers_connected.append(2)
    i2c_control2 = SoftI2C(scl=Pin(17), sda=Pin(16), freq = 200000)
    mux2 = PCA9548A(i2c_control2)
    mux2.select(1)
    oled_big2 = SH1107(i2c_control2, rotation=270)
    mux2.select(0)
    pcf2 = PCF8574(i2c_control2, 0x20)
    mux2.select(2)
    oled2 = SSD1306_I2C(128, 64, i2c_control2, addr=0x3D)

    #encoder = KY040_PCF(pcf, pin_clk_gpio=13, pin_dt_pcf=dt, pin_sw=sw)
    encoder2 = AdafruitEncoder(i2c_control2)

##################################################
if id_pin3.value() == 0:
    controllers_connected.append(3)
    mux3 = PCA9548A(i2c_control2)
    mux3.select(1)
    oled_big3 = SH1107(i2c_control2, rotation=270)
    mux3.select(0)
    pcf3 = PCF8574(i2c_control2, 0x20)
    mux3.select(2)
    oled3 = SSD1306_I2C(128, 64, i2c_control2, addr=0x3D)

    #encoder = KY040_PCF(pcf, pin_clk_gpio=13, pin_dt_pcf=dt, pin_sw=sw)
    encoder3 = AdafruitEncoder(i2c_control2)

##################################################
print(controllers_connected)

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

def change_arm_len(extend):
    if extend:
        if limit_switch.value() == 0: return
        extend_motor_1.high()
        extend_motor_2.low()
        sleep(5)
        extend_motor_1.high()
        extend_motor_2.high()
    else:
        if limit_switch.value() == 1: return
        extend_motor_1.low()
        extend_motor_2.high()
        while True:
            activate = limit_switch.value()
            print(activate)
            if activate == 1:
                break
            sleep(0.01)
        sleep(0.1)
        extend_motor_1.high()
        extend_motor_2.high()
def move_to_tile(tile, quick = False, backwards = True, stop = False, slow = False):
    
    # Convert sensor (-180 to 180) to 0-360
    raw = rotation_sensor.angle
    degree = raw % 360

    target = places[tile][1] 

    # Signed diff: positive = CW, negative = CCW
    diff = (target - degree) % 360
    if diff > 180:
        diff -= 360 

    
    move_degree = abs(diff)

    #CW = 0, CCW = 1
    direction = 0 if diff > 0 else 1

    if not quick:
        direction = 0  
        if diff < 0:   
            move_degree = 360 - move_degree


    speed = .005 if quick and not slow else .02
    move_degree = int((microstep*move_degree)/360)
    if backwards:
        direction = not direction
    step_motor(move_degree, direction, speed, base_dir, base_pul)
    if stop:
        return
    degree = raw % 360

    target = places[tile][1] 

    # Signed diff: positive = CW, negative = CCW
    diff = (target - degree) % 360
    if diff > 180:
        diff -= 360 
    move_degree = abs(diff)
    if move_degree > 3:
        move_to_tile(tile, True, backwards, True, True)


def roll_dice(oled, outcome, x=30, y=30, w=60, h=60, loops=1,):
    for _ in range(loops):
        for i in range(16):
            if i == 2:
                continue
            oled.fill(0)
            oled.draw_image("frame_{:02d}.img".format(i), x, y, w, h)
            oled.show()
    oled.fill(0)
    oled.text_scaled(str(outcome), x+15, y, 50)
    oled.show()
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

    DIR_PIN.value(not direction)  # Set direction
    for _ in range(steps):
        PUL_PIN.value(1)  # Pulse high
        sleep(delay)
        PUL_PIN.value(0)  # Pulse low
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

import random
import time
def shuffle(lst):
    for i in range(len(lst) - 1, 0, -1):
        j = random.randint(0, i)
        lst[i], lst[j] = lst[j], lst[i]
# used for going though turns
turn_thing = 0

def oled_big_text(controller_num, text, x = 0, y = 0, a =1, all = False):
    #controller_num = player_list[int(controller_num)-1].controller
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.text_wrapped(text, x, y, a)
        except IndexError:
            None
    if controller_num == 2 or all:
        mux2.select(1)
        try:    
            if not player_list[1].ai:
                oled_big2.text_wrapped(text, x, y, a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.text_wrapped(text, x, y, a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.text_wrapped(text, x, y, a)
        except IndexError:
            None
def oled_big_rect(controller_num, text, x = 0, y = 0, w = 10, h = 10, a = 1, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.rect(text, x, y, w, h, a)
        except IndexError:
            None
    if controller_num == 2 or all:
        mux2.select(1)
        try:    
            if not player_list[1].ai:
                oled_big2.rect(text, x, y, w, h, a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.rect(text, x, y, w, h, a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.rect(text, x, y, w, h, a)
        except IndexError:
            None
def oled_big_show(controller_num, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.show()
        except IndexError:
            None
    if controller_num == 2 or all:
        mux2.select(1)
        try:    
            if not player_list[1].ai:
                oled_big2.show()
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.show()
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.show()
        except IndexError:
            None
def oled_big_fill(controller_num, a = 0, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.fill(a)
        except IndexError:
            None
    if controller_num == 2 or all:
        mux2.select(1)
        try:    
            if not player_list[1].ai:
                oled_big2.fill(a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.fill(a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.fill(a)
        except IndexError:
            None
def oled_text(controller_num, text, x = 0, y = 0, a = 1, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled1.text(text, x, y, a)
        except IndexError:
            None
    if controller_num == 2 or all:
        mux2.select(2)
        try:    
            if not player_list[1].ai:
                oled2.text(text, x, y, a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled3.text(text, x, y, a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled4.text(text, x, y, a)
        except IndexError:
            None
def oled_show(controller_num, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled1.show()
        except IndexError:
            None
    if controller_num == 2 or all:
        mux2.select(2)
        try:    
            if not player_list[1].ai:
                oled2.show()
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled3.show()
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled4.show()
        except IndexError:
            None
def oled_fill(controller_num, a = 0, all = False, true_clear = False):
    
    if true_clear:
        if controller_num == 1 or all:
            try:    
                if not player_list[0].ai:
                    oled1.fill(a)
            except IndexError:
                None
        if controller_num == 2 or all:
            mux2.select(2)
            try:    
                if not player_list[1].ai:
                    oled2.fill(a)
            except IndexError:
                None
        if controller_num == 3 or all:
            try:    
                if not player_list[2].ai:
                    oled3.fill(a)
            except IndexError:
                None
        if controller_num == 4 or all:
            try:    
                if not player_list[3].ai:
                    oled4.fill(a)  
            except IndexError:
                None
    else:
        if controller_num == 1 or all:
            try:    
                if not player_list[0].ai:
                    oled1.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
        if controller_num == 2 or all:
            mux2.select(2)
            try:    
                if not player_list[1].ai:
                    oled2.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
        if controller_num == 3 or all:
            try:    
                if not player_list[2].ai:
                    oled3.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
        if controller_num == 4 or all:
            try:    
                if not player_list[3].ai:
                    oled4.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
def oled_rect(controller_num, x, y, w, h, a = 1, fill = True, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled1.rect(x, y, w, h, a, fill)
        except IndexError:
            None
    if controller_num == 2 or all:
        mux2.select(2)
        try:    
            if not player_list[1].ai:
                oled2.rect(x, y, w, h, a, fill)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled3.rect(x, y, w, h, a, fill)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled4.rect(x, y, w, h, a, fill)
        except IndexError:
            None
def pcf_pin(pcf_num, color):

    if pcf_num == 1:
        try:    
            if not player_list[0].ai:
                return pcf1.pin(color)
        except IndexError:
            None
    if pcf_num == 2:
        mux2.select(0)
        try:    
            if not player_list[1].ai:
                return pcf2.pin(color)
        except IndexError:
            None
    if pcf_num == 3:
        try:    
            if not player_list[2].ai:
                return pcf3.pin(color)
        except IndexError:
            None
    if pcf_num == 4:
        try:    
            if not player_list[3].ai:
                return pcf4.pin(color)
        except IndexError:
            None

def encoder(enc_num, dos):
    if dos == "delta":
        if enc_num == 1:
            try:    
                if not player_list[0].ai:
                    return encoder1.get_delta()
            except IndexError:
                None
        if enc_num == 2:
            mux2.select(0)
            try:    
                if not player_list[1].ai:
                    return encoder2.get_delta()
            except IndexError:
                None
        if enc_num == 3:
            try:    
                if not player_list[2].ai:
                    return encoder3.get_delta()
            except IndexError:
                None
        if enc_num == 4:
            try:    
                if not player_list[3].ai:
                    return encoder4.get_delta()
            except IndexError:
                None   
    if dos == "switch":
        if enc_num == 1:
            try:    
                if not player_list[0].ai:
                    return encoder1.get_switch()
            except IndexError:
                None
        if enc_num == 2:
            mux2.select(0)
            try:    
                if not player_list[1].ai:
                    return encoder2.get_switch()
            except IndexError:
                None
        if enc_num == 3:
            try:    
                if not player_list[2].ai:
                    return encoder3.get_switch()
            except IndexError:
                None
        if enc_num == 4:
            try:    
                if not player_list[3].ai:
                    return encoder4.get_switch()
            except IndexError:
                None   
# creates classes to store information about players, title_deeds, etc.
class chests:
    def __init__(self, name, money, jail_card, place):
        self.name = name
        self.money = money
        self.jail_card = jail_card
        self.place = place


class chances:
    def __init__(self, name, money, jail_card, place):
        self.name = name
        self.money = money
        self.jail_card = jail_card
        self.place = place


class title_deeds:
    def __init__(self, place, buy, house_buy, hotel_buy, base_rent, rent_house, rent_house1, rent_house2, rent_house3, rent_hotel, color, num_houses, colorset, num_house, num_hotel, rent, mortgage):
        self.place = place
        self.buy = buy
        self.house_buy = house_buy
        self.hotel_buy = hotel_buy
        self.base_rent = base_rent
        self.rent_house = rent_house
        self.rent_house1 = rent_house1
        self.rent_house2 = rent_house2
        self.rent_house3 = rent_house3
        self.rent_hotel = rent_hotel
        self.color = color
        self.num_houses = num_houses
        self.colorset = colorset
        self.num_house = num_house
        self.num_hotel = num_hotel
        self.rent = rent
        self.mortgage = mortgage
        self.calc_rent()

    # function to calculate rent
    def calc_rent(self):
        if self.num_hotel > 0:
            self.rent = self.rent_hotel
        elif self.num_house == 1:
            self.rent = self.rent_house
        elif self.num_house == 2:
            self.rent = self.rent_house1
        elif self.num_house == 3:
            self.rent = self.rent_house2
        elif self.num_house == 4:
            self.rent = self.rent_house3
        else:
            self.rent = self.base_rent
        return self.rent

    # functiont to calculate selling price
    def calc_sell(self):
        sell = 0
        sell += self.buy / 2
        sell += self.num_house * (self.house_buy / 2)
        sell += self.num_hotel * (self.hotel_buy / 2)
        return sell


class utilities:
    def __init__(self, name, buy, mortgage):
        self.name = name
        self.buy = buy
        self.mortgage = mortgage


class trains:
    def __init__(self, name, buy, mortgage):
        self.name = name
        self.buy = buy
        self.mortgage = mortgage


class specials:
    def __init__(self, name, money, jail):
        self.name = name
        self.money = money
        self.jail = jail


class players:
    def __init__(self, token, title_deeds, house, hotel, balance, position, jail_card, jail, ai, mortgaged_p, auction, time_in_jail, controller):
        self.token = token
        self.title_deeds = title_deeds
        self.house = house
        self.hotel = hotel
        self.balance = balance
        self.position = position
        self.jail_card = jail_card
        self.jail = jail
        self.ai = ai
        self.mortgaged_p = mortgaged_p
        self.auction = auction
        self.time_in_jail = time_in_jail
        self.controller = controller
    def append_title_deed(self, title_deed):
        self.title_deeds.append(title_deed)


# functions used to open and create save files
save_files = []


def save_file(file_name, classes):
    a = open(file_name, "w")
    b = str(classes)
    a.write(b)
    a.close()
    # print("saved")


def open_file(file_name, player_list):
    a = open(file_name, "r")
    c = eval(a.read())
    # Add code for extracting info from lists below and set equal to classes
    for i in range(len(player_list)):
        player_list[i].token = c[i][0]
        player_list[i].title_deeds = c[i][1]
        player_list[i].house = c[i][2]
        player_list[i].hotel = c[i][3]
        player_list[i].balance = c[i][4]
        player_list[i].position = c[i][5]
        player_list[i].jail_card = c[i][6]
        player_list[i].jail = c[i][7]
        player_list[i].ai = c[i][8]
    return player_list


# function that runs teh open and save files functions
def save(save_name):
    list_of_list_of_classes = []
    # makes a list and saves the list
    for i in range(len(player_list)):
        list_of_classes = []
        list_of_classes.append(player_list[i].token)
        list_of_classes.append(player_list[i].title_deeds)
        list_of_classes.append(player_list[i].house)
        list_of_classes.append(player_list[i].hotel)
        list_of_classes.append(player_list[i].balance)
        list_of_classes.append(player_list[i].position)
        list_of_classes.append(player_list[i].jail_card)
        list_of_classes.append(player_list[i].jail)
        list_of_classes.append(player_list[i].ai)
        list_of_list_of_classes.append(list_of_classes)
    save_file(save_name + "player_list.txt", list_of_list_of_classes)


# function to open up saves
def open_save(save_name, list_of_list_of_classes):
    list_of_list_of_classes = open_file(
        save_name + "player_list.txt", list_of_list_of_classes
    )
    return player_list
def update_info(turn):
    if player_list[turn].ai == True:
        return
    oled_fill(int(player_list[turn].controller), true_clear = True)
    oled_text(int(player_list[turn].controller), f"${player_list[turn].balance}", 0, 0, 1)
    oled_text(int(player_list[turn].controller), f"Pos:{player_list[turn].position}", 80, 0, 1)
    oled_show(int(player_list[turn].controller))
def move_player(start, target, backwards = False):
    change_arm_len(True)
    move_to_tile(start, quick = True)
    time.sleep(.5)
    magnet.high()
    change_arm_len(False)
    move_to_tile(target, backwards)
    time.sleep(.5)
    change_arm_len(True)
    magnet.low()
save_file_of_save_file_of_save_files = open("save_file_of_save_files.txt", "r")
save_files = eval(save_file_of_save_file_of_save_files.read())
# creates the players.


player_num = 2
oled_big1.fill(0)
oled_big1.show()
oled1.fill(0)
oled1.text("Monopoly Set Up", 0, 0, 1)
oled1.text("Enter # players", 0, 16, 1)
while True:
    oled1.rect(0, 26, 128, 20, 0, True)
    oled1.text(f"# of players: {player_num}", 0, 26, 1)
    oled1.show()
    player_num += encoder1.get_delta()
    if player_num < 2:
        player_num = 2
    elif player_num > 4:
        player_num = 4
    if encoder1.get_switch() == 0:
        if player_num-1>len(controllers_connected):
            oled1.rect(0, 26, 128, 10, 0, True)
            oled1.text("Dont have enough ", 0, 26, 1)
            oled1.text("controllers", 0, 36, 1)
            oled1.show()
            sleep(2)
        else:
            break
player_list = []

for i in range(player_num):
    oled1.rect(0, 16, 128, 20, 0, True)
    token = str(i+1)
    oled1.text(f"Is player {token} ai?", 0, 16, 1)
    oled1.text("<-no       yes->", 0, 46, 1)
    oled1.show()
    while True:
        #print(pcf1.pin(yellow), pcf1.pin(green))
        time.sleep(.1)
        if pcf1.pin(yellow) == 0:
            ai = False
            controller = controllers_connected[0]
            controllers_connected.pop(0)
            time.sleep(.3)
            break
        if pcf1.pin(green) == 0:
            ai = True
            controller = -1
            time.sleep(.3)
            break
    player_list.append(players(token, [], 0, 0, 1500, 0, False, False, ai, [], True, 0, controller))
# asks if they want to open up a previous save file
oled1.rect(0, 16, 128, 20, 0, True)
oled1.text("Open save files?", 0, 16, 1)
oled1.text("Req same player#", 0, 26, 1)
oled1.text("<-no       yes->", 0, 46, 1)
oled1.show()
while True:

    if pcf1.pin(green) == 0:
        oled1.rect(0, 16, 128, 20, 0, True)
        print(save_files)
        oled_big1.text("Which save file", 0, 0, 1)
        oled_big1.show()
        save_file_num = len(save_files)
        save_name = 0
        while True:
            oled_big1.rect(0, 15, 20, 30, 0, True)
            oled_big1.text(str(save_files[save_name]), 0, 15, 1)
            oled_big1.show()
            save_name += encoder1.get_delta()
            if save_name < 0:
                save_name = 0
            if save_name > save_file_num-1:
                save_name = save_file_num-1
            if encoder1.get_switch() == 0:
                open_save_file = str(save_files[save_name])
                time.sleep(.3)
                break
        oled_big1.fill(0)
        oled_big1.show()
        player_list = open_save(open_save_file, player_list)
        break
    if pcf1.pin(yellow) == 0:
        oled1.rect(0, 16, 128, 30, 0, True)
        time.sleep(.3)
        break
oled1.text("Set up finished", 0, 16, 1)
oled1.show()
time.sleep(2)
oled1.fill(0)
oled1.show()
# makes a list of classes for the title_deeds, cards, etc.
community_chest = [
    chests("Pay school tax", -50, False, ""),
    chests("collect $50 from every player", 50 * len(player_list), False, "get_50"),
    chests("You inherit $100", 100, False, ""),
    chests("pay hospital $100", -100, False, ""),
    chests("income tax refund", 50, False, ""),
    chests("go to jail", 0, False, "Jail"),
    chests("get out of jail free card", 0, True, ""),
    chests("second place prize in beauty contest, +$10", 10, False, ""),
    chests(
        "pay $40 per house and $115 for every hotel",
        -40 * player_list[0].house + -115 * player_list[0].hotel,
        False,
        "",
    ),
    chests("bank error, collect $200", 200, False, ""),
    chests("Advance to go", 0, False, "Go"),
    chests("IMA fund matures, collect $100", 100, False, ""),
    chests("doctors fee of $50", -50, False, ""),
    chests("sale of stock, $45", 45, False, ""),
    chests("$25 for services", 25, False, ""),
    chests("Life insurance matures, collect $100", 100, False, ""),
]
chance_card = [
    chances("Advance to St. Charles", 0, False, "St. Charles"),
    chances("Get out of jail free card", 0, True, ""),
    chances("Take a ride to a train station", 0, False, "Train Station"),
    chances("Advance to Illinois Ave", 0, False, "Illinois Ave"),
    chances(
        "repairs, pay $25 per house and $100 per hotel",
        -35 * player_list[0].house + -100 * player_list[0].hotel,
        False,
        "",
    ),
    chances("advance to go", 0, False, "Go"),
    chances("banks pays $50", 50, False, ""),
    chances("Pay poor tax of $15", -15, False, ""),
    chances("Advance to nearst Utility", 0, False, "Placeholder for nearest utility"),
    chances("Go to Jail", 0, False, "Jail"),
    chances("Elected chairman, pay $50 per player", -50 * player_num, False, "pay_50"),
    chances("Advance to Boardwalk", 0, False, "Boardwalk"),
    chances(
        "Go back 3 spaces", 0, False, "placeholder for player position minus 3 spaces"
    ),
    chances(
        "advance to nearest railroad", 0, False, "Placeholder for nearest railroad"
    ),
    chances("Buildings and loan matures, collect $150", 150, False, ""),
]
title_deed = [
    title_deeds("Mediterranean Ave", 60, 50, 50, 2, 10, 30, 90, 160, 250, "brown", 0, False, 0, 0, 0, False),
    title_deeds("Baltic Ave", 60, 50, 50, 4, 20, 60, 180, 320, 450, "brown", 0, False, 0, 0, 0, False),
    title_deeds("Oriental Ave", 100, 50, 50, 6, 30, 90, 270, 400, 550, "light blue", 0, False, 0, 0, 0, False),
    title_deeds("Vermont Ave", 100, 50, 50, 6, 30, 90, 270, 400, 550, "light blue", 0, False, 0, 0, 0, False),
    title_deeds("Connecticut Ave", 120, 50, 50, 8, 40, 100, 300, 450, 600, "light blue", 0, False, 0, 0, 0, False),
    title_deeds("St. Charles Place", 140, 100, 100, 10, 50, 150, 450, 625, 750, "pink", 0, False, 0, 0, 0, False),
    title_deeds("States Ave", 140, 100, 100, 10, 50, 150, 450, 625, 750, "pink", 0, False, 0, 0, 0, False),
    title_deeds("Virginia Ave", 160, 100, 100, 12, 60, 180, 500, 700, 900, "pink", 0, False, 0, 0, 0, False),
    title_deeds("St. James Place", 180, 100, 100, 14, 70, 200, 550, 750, 950, "orange", 0, False, 0, 0, 0, False),
    title_deeds("Tennessee Ave", 180, 100, 100, 14, 70, 200, 550, 750, 950, "orange", 0, False, 0, 0, 0, False),
    title_deeds("New York Ave", 200, 100, 100, 16, 80, 220, 600, 800, 1000, "orange", 0, False, 0, 0, 0, False),
    title_deeds("Kentucky Ave", 220, 150, 150, 18, 90, 250, 700, 875, 1050, "red", 0, False, 0, 0, 0, False),
    title_deeds("Indiana Ave", 220, 150, 150, 18, 90, 250, 700, 875, 1050, "red", 0, False, 0, 0, 0, False),
    title_deeds("Illinois Ave", 240, 150, 150, 20, 100, 300, 750, 925, 1100, "red", 0, False, 0, 0, 0, False),
    title_deeds("Atlantic Ave", 260, 150, 150, 22, 110, 330, 800, 975, 1150, "yellow", 0, False, 0, 0, 0, False),
    title_deeds("Ventnor Ave", 260, 150, 150, 22, 110, 330, 800, 975, 1150, "yellow", 0, False, 0, 0, 0, False),
    title_deeds("Marvin Gardens", 280, 150, 150, 24, 120, 360, 850, 1025, 1200, "yellow", 0, False, 0, 0, 0, False),
    title_deeds("Pacific Ave", 300, 200, 200, 26, 130, 390, 900, 1100, 1275, "green", 0, False, 0, 0, 0, False),
    title_deeds("North Carolina Ave", 300, 200, 200, 26, 130, 390, 900, 1100, 1275, "green", 0, False, 0, 0, 0, False),
    title_deeds("Pennsylvania Ave", 320, 200, 200, 28, 150, 450, 1000, 1200, 1400, "green", 0, False, 0, 0, 0, False),
    title_deeds("Park Place", 350, 200, 200, 35, 175, 500, 1100, 1300, 1500, "blue", 0, False, 0, 0, 0, False),
    title_deeds("Boardwalk", 400, 200, 200, 50, 200, 600, 1400, 1700, 2000, "blue", 0, False, 0, 0, 0, False),
]
utility = [
    utilities("Electric Company", 150, False),
    utilities("Water Works", 150, False),
]
train = [
    trains("Reading Railroad", 200, False),
    trains("Pennsylvania Railroad", 200, False),
    trains("B. & O. Railroad", 200, False),
    trains("Short Line", 200, False),
]
special = [
    specials("Go", 200, False),
    specials("Jail", 0, True),
    specials("Free Parking", 0, False),
    specials("Go to jail", 0, False),
    specials("Income tax", -200, False),
    specials("Luxury tax", -100, False),
]
# list used for seperating title_deeds into a list by color set for color set function
colorsets = [
    ["Mediterranean Ave", "Baltic Ave"],
    ["Oriental Ave", "Vermont Ave", "Connecticut Ave"],
    ["St. Charles Place", "States Ave", "Virginia Ave"],
    ["St. James Place", "Tennessee Ave", "New York Ave"],
    ["Kentucky Ave", "Indiana Ave", "Illinois Ave"],
    ["Atlantic Ave", "Ventnor Ave", "Marvin Gardens"],
    ["Pacific Ave", "North Carolina Ave", "Pennsylvania Ave"],
    ["Park Place", "Boardwalk"],
]

# function used for finding if a title_deed is in a colorset
def check_color_set(turn, ai=False):
    player = player_list[turn]
    player_deeds_set = set(player.title_deeds)  # fast lookups
    found_colorset = False
    announced = False

    for colorset in colorsets:
        # Check if the player owns every deed in this colorset
        if set(colorset).issubset(player_deeds_set):
            if not announced:
                print("You have a color set")
                announced = True
            found_colorset = True

            # Mark each matching title_deed object
            for deed in title_deed:
                if deed.place in colorset:
                    deed.colorset = True

    if ai:
        return found_colorset
    else:
        return title_deed, player_list
    """thing = True
    colorset = False
    # goes through owned title_deeds
    for i in range(len(player_list[turn].title_deeds)):
        # goes through each colorset
        for j in range(len(colorsets)):
            # goes through each owned title deed and match it to a colorset
            if player_list[turn].title_deeds[i] in colorsets[j]:
                # sees if the color set contains 2 or 3 properties
                if len(colorsets[j]) == 2:
                    # goes through each owned title deed
                    for k in range(len(player_list[turn].title_deeds)):
                        # finds teh colorset of the title deed
                        if player_list[turn].title_deeds[k] == colorsets[j][0]:
                            # goes through each title deed again
                            for l in range(len(player_list[turn].title_deeds)):
                                # sees if the title deed is in teh same color set
                                # The branch for 3 title deed does this step again
                                if player_list[turn].title_deeds[l] == colorsets[j][1]:
                                    # goes though each title deed
                                    for m in range(len(title_deed)):
                                        # matches teh title deed in a list to teh list of title deed classes
                                        if (
                                            title_deed[m].place
                                            == player_list[turn].title_deeds[k]
                                        ):
                                            if thing == True:
                                                print("You have a color set")
                                                thing = False
                                            if ai == True:
                                                colorset = True
                                            # makes the colorset value true
                                            title_deed[m].colorset = True
                                            title_deed[m + 1].colorset = True
                if len(colorsets[j]) == 3:
                    for k in range(len(player_list[turn].title_deeds)):
                        if player_list[turn].title_deeds[k] == colorsets[j][0]:
                            for l in range(len(player_list[turn].title_deeds)):
                                if player_list[turn].title_deeds[l] == colorsets[j][1]:
                                    for m in range(len(player_list[turn].title_deeds)):
                                        if (
                                            player_list[turn].title_deeds[m]
                                            == colorsets[j][2]
                                        ):
                                            for n in range(len(title_deed)):
                                                if (
                                                    title_deed[m].place
                                                    == player_list[turn].title_deeds[k]
                                                ):
                                                    if thing == True:
                                                        print("You have a color set")
                                                        thing = False
                                                    if ai == True:
                                                        colorset = True
                                                    title_deed[m].colorset = True
                                                    title_deed[m + 1].colorset = True
    if ai == False:
        return title_deed, player_list
    if ai == True:
        return colorset"""


def broke(turn, reciver, player_list, negative):

    # ── helpers ──────────────────────────────────────────────────────────────

    def find_player_index(token):
        """Return the index in player_list whose token matches `token`."""
        for idx, p in enumerate(player_list):
            if p.token == token:
                return idx
        return None

    def find_td_index(deed_name):
        """
        Return (category, index) for deed_name.
        category is one of: "title_deed", "train", "utility"
        Returns (None, None) if not found.
        FIX: previously only searched title_deed, causing wrong indices for
        railroads/utilities.
        """
        for i, td in enumerate(title_deed):
            if td.place == deed_name:
                return "title_deed", i
        for i, rr in enumerate(train):
            if rr.name == deed_name:
                return "train", i
        for i, ut in enumerate(utility):
            if ut.name == deed_name:
                return "utility", i
        return None, None

    def calc_sell_value(category, idx):
        """
        Return the sell value for a property.
        FIX: previously always called title_deed[idx].calc_sell() even for
        railroads/utilities, which used the wrong object or crashed.
        """
        if category == "title_deed":
            return title_deed[idx].calc_sell()
        elif category == "train":
            return 100   # standard Monopoly mortgage value for railroads
        elif category == "utility":
            return 75    # standard Monopoly mortgage value for utilities
        return 0

    def selling_td(sell_t, sell, p_list, category, td_idx, actor_turn, actor_receiver):
        """
        Transfer or sell one property.
        FIX: signature now takes explicit category + index so railroads and
        utilities are handled correctly, and actor_turn/actor_receiver are
        explicit rather than captured from the outer scope.
        """
        p_list[actor_turn].title_deeds.remove(sell_t)

        if sell == "trade":
            recv_idx = find_player_index(actor_receiver)
            p_list[recv_idx].title_deeds.append(sell_t)

        elif sell == "sell":
            p_list[actor_turn].balance += calc_sell_value(category, td_idx)
            update_info(actor_turn)

        else:  # "sell_and_give"
            recv_idx = find_player_index(actor_receiver)
            p_list[recv_idx].title_deeds.append(sell_t)
            p_list[actor_turn].balance += calc_sell_value(category, td_idx)
            update_info(actor_turn)

        time.sleep(2)
        return p_list

    # ── pick a title deed to give (UI helper) ────────────────────────────────

    def pick_td_from_player(picker_turn, prompt="What title deed do you want to give"):
        """
        Let the human or AI at picker_turn choose one of their title deeds.
        Returns the deed name chosen, or None if they have none.
        FIX: extracted into its own helper so the same logic isn't duplicated
        for both sides of a trade.
        """
        if not player_list[picker_turn].title_deeds:
            return None

        if player_list[picker_turn].ai:
            return AI(player_list, "td_to_give", 0, 0, picker_turn,
                      player_list[picker_turn].token)

        ctrl = int(player_list[picker_turn].controller)
        oled_big_text(ctrl, prompt, 0, 0, 1)
        oled_big_show(ctrl)

        tds_owned = len(player_list[picker_turn].title_deeds)
        td_to_show = 0
        while True:
            oled_rect(ctrl, 0, 36, 128, 10, 0, True)
            oled_text(ctrl, player_list[picker_turn].title_deeds[td_to_show], 0, 36, 1)
            oled_show(ctrl)
            td_to_show = (td_to_show + encoder(ctrl, "delta")) % tds_owned
            if encoder(ctrl, "switch") == 0:
                chosen = player_list[picker_turn].title_deeds[td_to_show]
                oled_big_fill(ctrl)
                oled_big_text(ctrl, "You chose to give", 0, 0, 1)
                oled_big_text(ctrl, chosen, 0, 15, 1)
                oled_big_show(ctrl)
                time.sleep(1)
                oled_big_fill(ctrl); oled_big_show(ctrl)
                oled_fill(ctrl);     oled_show(ctrl)
                return chosen

    # ── TRADE branch ─────────────────────────────────────────────────────────

    if reciver != 0:

        # --- current player gives a deed ---
        while True:
            td_to_give = pick_td_from_player(turn)
            if td_to_give is None:
                print("No title deeds to give")
                time.sleep(2)
                break

            category, idx = find_td_index(td_to_give)
            if category is None:
                print("Please select a valid title deed")
                time.sleep(2)
                continue

            if category == "title_deed" and title_deed[idx].colorset:
                print("You cannot trade off a title deed in a colorset")
                time.sleep(2)
                continue

            break   # valid selection

        player_list = selling_td(td_to_give, "trade", player_list,
                                 category, idx, turn, reciver)

        # --- receiver gives a deed back ---
        recv_turn = find_player_index(reciver)

        while True:
            td_to_receive = pick_td_from_player(recv_turn,
                                                "What title deed do you want to give back")
            if td_to_receive is None:
                print("No title deeds to give back")
                time.sleep(2)
                break

            # FIX: was only searching title_deed; now uses find_td_index
            recv_cat, recv_idx = find_td_index(td_to_receive)
            if recv_cat is None:
                print("Please select a valid title deed")
                time.sleep(2)
                continue

            if recv_cat == "title_deed" and title_deed[recv_idx].colorset:
                print("You cannot trade off a title deed in a colorset")
                time.sleep(2)
                continue

            break

        # FIX: pass explicit actor_turn=recv_turn and actor_receiver=player's token
        player_list = selling_td(td_to_receive, "trade", player_list,
                                 recv_cat, recv_idx,
                                 actor_turn=recv_turn,
                                 actor_receiver=player_list[turn].token)

    # ── BANKRUPTCY branch ────────────────────────────────────────────────────

    elif player_list[turn].balance < 0 and not negative:
        # FIX: `negative` is a plain bool check; was `negative == False`

        while True:
            if not player_list[turn].title_deeds:
                # ── GAME OVER ──────────────────────────────────────────────
                print("Game Over")
                oled_big_text(int(player_list[turn].controller),
                              "Game Over", 0, 0, 1, all=True)
                oled_big_show(int(player_list[turn].controller), all=True)
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller), all=True)
                oled_big_show(int(player_list[turn].controller), all=True)

                # FIX: liquidate all players' assets (not just the bankrupt player),
                # using the correct per-player turn index and proper category lookup.
                for i in range(len(player_list)):
                    for deed in list(player_list[i].title_deeds):
                        cat, td_idx = find_td_index(deed)
                        if td_idx is not None:
                            player_list = selling_td(deed, "sell", player_list,
                                                     cat, td_idx,
                                                     actor_turn=i,
                                                     actor_receiver=0)
                            update_info(i)

                # FIX: sort by balance descending to assign places correctly
                ranked = sorted(range(len(player_list)),
                                key=lambda i: player_list[i].balance,
                                reverse=True)
                places = ["First", "Second", "Third", "Fourth"]
                for rank, i in enumerate(ranked):
                    if rank < len(places):
                        print(f"{places[rank]},", player_list[i].token)
                        oled_big_text(int(player_list[i].token),
                                      f"{places[rank]} place", 0, 0, 1, all=True)
                        oled_big_text(int(player_list[i].token),
                                      player_list[i].token, 0, 15, 1, all=True)
                        oled_big_show(int(player_list[i].token), all=True)
                        time.sleep(2)
                        oled_big_fill(int(player_list[i].token), all=True)
                        oled_big_show(int(player_list[i].token), all=True)

                raise ValueError("Game Over")

            # ── still has deeds: ask what to sell / mortgage ───────────────
            print(player_list[turn].title_deeds)

            if player_list[turn].ai:
                sell_t = AI(player_list, "sell_t", 0, 0, turn)
                # FIX: was `mos = 1` which is truthy but not "mortgage";
                # AI always mortgages here, so set it explicitly.
                mos = "mortgage"
            else:
                ctrl = int(player_list[turn].controller)

                # pick which deed
                while True:
                    oled_big_text(ctrl,
                                  "You have to sell or mortgage a title deed. Which one?",
                                  0, 0, 1)
                    oled_big_show(ctrl)
                    tds_owned = len(player_list[turn].title_deeds)
                    td_to_show = 0
                    while True:
                        oled_rect(ctrl, 0, 36, 128, 10, 1, True)
                        oled_text(ctrl, player_list[turn].title_deeds[td_to_show], 0, 36, 1)
                        oled_show(ctrl)
                        td_to_show = (td_to_show + encoder(ctrl, "delta")) % tds_owned
                        if encoder(ctrl, "switch") == 0:
                            sell_t = player_list[turn].title_deeds[td_to_show]
                            oled_big_text(ctrl, "You chose", 0, 0, 1)
                            oled_big_text(ctrl, sell_t, 0, 15, 1)
                            oled_big_show(ctrl)
                            break
                    time.sleep(2)
                    oled_big_fill(ctrl); oled_big_show(ctrl)
                    oled_fill(ctrl);     oled_show(ctrl)

                    cat_check, _ = find_td_index(sell_t)
                    if cat_check is not None:
                        break
                    print("Type a valid input")
                    time.sleep(2)

                # mortgage or sell?
                oled_big_text(ctrl, "Mortgage or sell", 0, 0, 1)
                oled_big_show(ctrl)
                oled_text(ctrl, "<-mortgage   $->", 0, 46, 1)
                oled_show(ctrl)
                mos = None   # FIX: explicit None so we never fall through with garbage
                while mos is None:
                    if pcf_pin(ctrl, green) == 0:
                        mos = "sell"
                        time.sleep(0.3)
                    elif pcf_pin(ctrl, yellow) == 0:
                        mos = "mortgage"
                        time.sleep(0.3)
                time.sleep(2)
                oled_big_fill(ctrl); oled_big_show(ctrl)
                oled_fill(ctrl);     oled_show(ctrl)

            # FIX: look up category + index once, used by both branches below
            category, td_idx = find_td_index(sell_t)

            if mos == "mortgage":
                if category == "title_deed":
                    title_deed[td_idx].mortgage = True
                    player_list[turn].balance += title_deed[td_idx].calc_sell() * 0.5
                    # sell back any buildings
                    list_of_td = [td.place for td in title_deed]
                    prop_idx = list_of_td.index(sell_t)
                    group = list_of_td.index(sell_t)
                    # refund per-group house cost
                    if prop_idx < 5:
                        house_val = 50
                    elif prop_idx < 11:
                        house_val = 100
                    elif prop_idx < 17:
                        house_val = 150
                    else:
                        house_val = 200
                    player_list[turn].balance += house_val * title_deed[td_idx].num_house
                    player_list[turn].balance += house_val * title_deed[td_idx].num_hotel
                    player_list[turn].house  -= title_deed[td_idx].num_house
                    player_list[turn].hotel  -= title_deed[td_idx].num_hotel
                    title_deed[td_idx].num_house = 0
                    title_deed[td_idx].num_hotel = 0

                elif category == "train":
                    train[td_idx].mortgage = True
                    player_list[turn].balance += 100

                elif category == "utility":
                    utility[td_idx].mortgage = True
                    player_list[turn].balance += 75

                player_list[turn].mortgaged_p.append(sell_t)
                player_list[turn].title_deeds.remove(sell_t)
                update_info(turn)

                msg = f"{sell_t} has been mortgaged and all buildings sold"
                print(msg)
                oled_big_text(int(player_list[turn].controller), msg, 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))

            else:  # sell
                # FIX: was breaking out of the loop without actually calling
                # selling_td; now calls it properly with correct category+index.
                if category is not None:
                    player_list = selling_td(sell_t, "sell", player_list,
                                             category, td_idx,
                                             actor_turn=turn,
                                             actor_receiver=reciver)

            if player_list[turn].balance >= 0:
                return player_list

            print("You still have a negative balance!")
            oled_big_text(int(player_list[turn].controller),
                          "You still have a negative balance!", 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(2)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))

    return player_list
"""def broke(turn, reciver, player_list, negative):
    # moves ownership of title deeds
    def selling_td(sell_t, sell, player_list, td_index, turn=turn, reciver=reciver):
        player_list[turn].title_deeds.remove(sell_t)
        if sell == "trade":
            for i in range(len(player_list)):
                if player_list[i].token == reciver:
                    break
            player_list[i].title_deeds.append(sell_t)
        elif sell == "sell":
            player_list[turn].balance += title_deed[td_index].calc_sell()
            update_info(turn)
        else:
            for i in range(len(player_list)):
                if player_list[i].token == reciver:
                    break
            player_list[i].title_deeds.append(sell_t)
            player_list[turn].balance += title_deed[td_index].calc_sell()
            update_info(turn)
        time.sleep(2)
        return player_list

    # if the broke function is called for trade, reciver is a name
    # if the function is used for seeing if someone is broke, then the reciver is 0
    if reciver != 0:
        while True:
            if player_list[turn].ai == True:
                td_to_give = AI(player_list, "td_to_give", 0, 0, turn, reciver)
            else:
                #td_to_give = input("What title deed do you want to give: ")
                oled_big_text(int(player_list[turn].controller), "What title deed do you want to give", 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                tds_owned = len(player_list[turn].title_deeds)
                td_to_show = 0
                while True:
                    oled_rect(int(player_list[turn].controller), 0, 36, 128, 10, 1, True)
                    oled_text(int(player_list[turn].controller), player_list[turn].title_deeds[td_to_show], 0, 36, 1)
                    oled_show(int(player_list[turn].controller))
                    td_to_show += encoder(int(player_list[turn].controller), "delta" )
                    if td_to_show < 0:
                        td_to_show = tds_owned-1
                    if td_to_show > tds_owned-1:
                        td_to_show = 0
                    if encoder(int(player_list[turn].controller), "switch" ) == 0:
                        oled_big_text(int(player_list[turn].controller), "You chose to give", 0, 0, 1)
                        oled_big_text(int(player_list[turn].controller), player_list[turn].title_deeds[td_to_show], 0, 15, 1)
                        oled_big_show(int(player_list[turn].controller))
                        td_to_give = player_list[turn].title_deeds[td_to_show]
                        break
                time.sleep(1)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))
                oled_fill(int(player_list[turn].controller))
                oled_show(int(player_list[turn].controller))

            list_of_td = [title_deed[i].place for i in range(len(title_deed))]
            list_of_rr = [train[i].name for i in range(len(train))]
            list_of_utility = ["Electric Company", "Water Works"]
            if td_to_give in list_of_td:
                index_of_td = list_of_td.index(td_to_give)
                if title_deed[index_of_td].colorset == True:
                    print("You cannot trade off a title deed in a colorset")
                    time.sleep(2)
                else:
                    break
            elif td_to_give in list_of_rr:
                index_of_td = list_of_rr.index(td_to_give)
                break
            elif td_to_give in list_of_utility:
                index_of_td = list_of_utility.index(td_to_give)
                break
            else:
                print("Please type a valid input")
                time.sleep(2)
        selling_td(td_to_give, "trade", player_list, index_of_td)
        for i in range(len(player_list)):
            if player_list[i].token == reciver:
                break
        if player_list[i].ai == True:
            td_to_recive = AI(player_list, "td_to_give", 0, 0, i, reciver)
        else:
            #td_to_recive = input("What title deed do you want to give(The player that recived): ")
            oled_big_text(int(reciver), "What title deed do you want to give", 0, 0, 1)
            oled_big_show(int(reciver))
            for j in range(len(player_list)):
                if player_list[j].token == reciver:
                    break
            tds_owned = len(player_list[j].title_deeds)
            td_to_show = 0
            while True:
                oled_rect(int(reciver), 0, 36, 128, 10, 1, True)
                oled_text(int(reciver), player_list[j].title_deeds[td_to_show], 0, 36, 1)
                oled_show(int(reciver))
                td_to_show += encoder(int(player_list[turn].controller), "delta" )
                if td_to_show < 0:
                    td_to_show = tds_owned-1
                if td_to_show > tds_owned-1:
                    td_to_show = 0
                if encoder(int(player_list[turn].controller), "switch" ) == 0:
                    oled_big_text(int(reciver), "You chose to give", 0, 0, 1)
                    oled_big_text(int(reciver), player_list[j].title_deeds[td_to_show], 0, 15, 1)
                    oled_big_show(int(reciver))
                    td_to_recive = player_list[j].title_deeds[td_to_show]
                    break
            time.sleep(2)
            oled_big_fill(int(reciver))
            oled_big_show(int(reciver))
            oled_fill(int(reciver))
            oled_show(int(reciver))
        for i in range(len(title_deed)):
            if title_deed[i].place == td_to_recive:
                break
        for j in range(len(player_list)):
            if player_list[j].token == reciver:
                break
        selling_td(td_to_recive, "trade", player_list, i, j, player_list[turn].token)
    elif player_list[turn].balance < 0 and negative == False:
        while True:
            # runs while player has title deeds
            if player_list[turn].title_deeds != []:
                print(player_list[turn].title_deeds)
                mos = 1
                # asks if they want to mortgage or sell a property
                if player_list[turn].ai == True:
                    sell_t = AI(player_list, "sell_t", 0, 0, turn)
                    mos = "mortgage"
                if player_list[turn].ai != True:
                    while True:
                        #sell_t = input(f"You have to sell one of your title deeds or mortgage it. Which one do you want to sell or mortgage(Type the title deed name EXACTLY `):\n{player_list[turn].title_deeds}")
                        oled_big_text(int(player_list[turn].controller), "You have to sell one of your title deeds or mortgage it. Which one do you want to sell or mortgage", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        tds_owned = len(player_list[turn].title_deeds)
                        td_to_show = 0
                        while True:
                            oled_rect(int(player_list[turn].controller), 0, 36, 128, 10, 1, True)
                            oled_text(int(player_list[turn].controller), player_list[turn].title_deeds[td_to_show], 0, 36, 1)
                            oled_show(int(player_list[turn].controller))
                            td_to_show += encoder(int(player_list[turn].controller), "delta" )
                            if td_to_show < 0:
                                td_to_show = tds_owned-1
                            if td_to_show > tds_owned-1:
                                td_to_show = 0
                            if encoder(int(player_list[turn].controller), "switch" ) == 0:
                                oled_big_text(int(player_list[turn].controller), "You chose to give", 0, 0, 1)
                                oled_big_text(int(player_list[turn].controller), player_list[turn].title_deeds[td_to_show], 0, 15, 1)
                                oled_big_show(int(player_list[turn].controller))
                                sell_t = player_list[turn].title_deeds[td_to_show]
                                break
                        time.sleep(2)
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                        oled_fill(int(player_list[turn].controller))
                        oled_show(int(player_list[turn].controller))
                        list_of_td = [
                            title_deed[i].place for i in range(len(title_deed))
                        ]
                        list_of_rr = [train[i].name for i in range(len(train))]
                        list_of_utility = ["Electric Company", "Water Works"]
                        if (
                            sell_t in list_of_td
                            or sell_t in list_of_rr
                            or sell_t in list_of_utility
                        ):
                            break
                        else:
                            print("Type a valid input")
                            time.sleep(2)
                    mos = input("mortgage or sell: ")
                    oled_big_text(int(player_list[turn].controller), "Mortgage or sell", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    oled_text(int(player_list[turn].controller), "<-mortgage   $->", 0, 46, 1)
                    oled_show(int(player_list[turn].controller))
                    while True:
                        if pcf_pin(int(player_list[turn].controller), green) == 0:
                            mos = "sell"
                            time.sleep(.3)
                            break
                        if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                            mos = "mortgage"
                            time.sleep(.3)
                            break

                    time.sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    oled_fill(int(player_list[turn].controller))
                    oled_show(int(player_list[turn].controller))
                if mos == "mortgage":
                    # turns the value for mortgage to true
                    for i in range(len(title_deed)):
                        if title_deed[i].place == sell_t:
                            td_index = i
                            title_deed[i].mortgage = True
                            player_list[turn].balance += title_deed[i].calc_sell() * 0.5
                            update_info(turn)
                            break
                    for i in range(len(train)):
                        if train[i].name == sell_t:
                            td_index = i
                            train[i].mortgage = True
                            player_list[turn].balance += 100
                            update_info(turn)
                            break
                    for i in range(len(utility)):
                        if utility[i].name == sell_t:
                            td_index = i
                            utility[i].mortgage = True
                            player_list[turn].balance += 75
                            update_info(turn)
                            break
                    list_of_td = [title_deed[i].place for i in range(len(title_deed))]
                    player_list[turn].mortgaged_p.append(sell_t)
                    player_list[turn].title_deeds.remove(sell_t)
                    try:
                        if sell_t in list_of_td[:5]:
                            player_list[turn].balance += (
                                50 * title_deed[list_of_td.index(sell_t)].num_house
                            )
                            player_list[turn].balance += (
                                50 * title_deed[list_of_td.index(sell_t)].num_hotel
                            )
                        elif sell_t in list_of_td[5:11]:
                            player_list[turn].balance += (
                                100 * title_deed[list_of_td.index(sell_t)].num_house
                            )
                            player_list[turn].balance += (
                                100 * title_deed[list_of_td.index(sell_t)].num_hotel
                            )
                        elif sell_t in list_of_td[11:17]:
                            player_list[turn].balance += (
                                150 * title_deed[list_of_td.index(sell_t)].num_house
                            )
                            player_list[turn].balance += (
                                150 * title_deed[list_of_td.index(sell_t)].num_hotel
                            )
                        elif sell_t in list_of_td[17:]:
                            player_list[turn].balance += (
                                200 * title_deed[list_of_td.index(sell_t)].num_house
                            )
                            player_list[turn].balance += (
                                200 * title_deed[list_of_td.index(sell_t)].num_hotel
                            )
                        update_info(turn)
                        player_list[turn].house -= title_deed[
                            list_of_td.index(sell_t)
                        ].num_house
                        player_list[turn].hotel -= title_deed[
                            list_of_td.index(sell_t)
                        ].num_hotel
                        title_deed[list_of_td.index(sell_t)].num_house = 0
                        title_deed[list_of_td.index(sell_t)].num_hotel = 0
                    except ValueError:
                        None
                    print(
                        f"{sell_t} has been mortgaged and all buildings have been sold"
                    )
                    oled_big_text(int(player_list[turn].controller), f"{sell_t} has been mortgaged and all buildings have been sold", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    time.sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                else:
                    leave_loop = False
                    # The problem is that sometimes a rr or utility is chosen instead of a title deed
                    for i in range(len(title_deed)):
                        if title_deed[i].place == sell_t:
                            td_index = i
                            leave_loop = True
                            break
                    for i in range(len(train)):
                        if train[i].name == sell_t:
                            td_index = i
                            leave_loop = True
                            break
                    for i in range(len(utility)):
                        if utility[i].name == sell_t:
                            td_index = i
                            leave_loop = True
                            break
                    if leave_loop == True:
                        break
                    player_list = selling_td(sell_t, "give", player_list, td_index)
                if player_list[turn].balance >= 0:
                    return player_list
                else:
                    print("You still have a negative balance!")
                    oled_big_text(int(player_list[turn].controller), "You still have a negative balance!", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    time.sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
            else:
                # Runs if the person is still in debt and has no title deeds to sell or mortgage
                print("Game Over")
                
                print()
                oled_big_text(int(player_list[turn].controller), "Game Over", 0, 0, 1, all = True)
                oled_big_show(int(player_list[turn].controller), all = True)
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller), all = True)
                oled_big_show(int(player_list[turn].controller), all = True)
                list_winners = []
                # sells teh property of all players to see who has the highest balance
                for i in range(len(player_list)):
                    for x in range(len(player_list[i].title_deeds)):
                        player_list[i].balance += selling_td(
                            player_list[i].title_deeds[x], "sell", player_list, td_index
                        )
                        update_info(turn)
                        list_winners.append(player_list[i].balance)
                sorted(list_winners)
                # calculates the player with teh highest balance
                for i in range(len(player_list)):
                    next_player = False
                    if player_list[i].balance == list_winners[0]:
                        print("First,", player_list[i].name)
                        oled_big_text(int(player_list[i].token), "First place", 0, 0, 1, all = True)
                        oled_big_text(int(player_list[i].token), player_list[i].token, 0, 15, 1, all = True)
                        oled_big_show(int(player_list[i].token), all = True)
                        time.sleep(2)
                        oled_big_fill(int(player_list[i].token), all = True)
                        oled_big_show(int(player_list[i].token), all = True)
                        next_player = True
                    if (
                        player_list[i].balance == list_winners[1]
                        and next_player == True
                    ):
                        print("Second,", player_list[i].token)
                        oled_big_text(int(player_list[i].token), "Second place", 0, 0, 1, all = True)
                        oled_big_text(int(player_list[i].token), player_list[i].token, 0, 15, 1, all = True)
                        oled_big_show(int(player_list[i].token), all = True)
                        time.sleep(2)
                        oled_big_fill(int(player_list[i].token), all = True)
                        oled_big_show(int(player_list[i].token), all = True)
                raise ValueError("Game Over")
    return player_list"""

def auction(player_list, name, turn):  # FIX: added turn parameter
    player_move = 0
    auction_price = 0
    must_win = 0
    print(f"Auction for {name} has started")
    oled_big_text(int(player_list[turn].controller), "Auction for", 0, 0, 1, all=True)
    oled_big_text(int(player_list[turn].controller), name, 0, 15, 1, all=True)
    oled_big_text(int(player_list[turn].controller), "has started", 0, 25, 1, all=True)
    oled_big_show(int(player_list[turn].controller), all=True)
    time.sleep(2)
    oled_big_fill(int(player_list[turn].controller), all=True)
    oled_big_show(int(player_list[turn].controller), all=True)

    for i in range(len(title_deed)):
        if title_deed[i].place == name:
            break

    while True:
        if player_list[player_move].auction == True:
            if player_list[player_move].ai == True:
                bid = AI(player_list, "bid", auction_price, i, turn)
                if bid == "no":
                    print("asdf")
                if must_win > 3:
                    bid = "yes"
                    must_win = 0
            else:
                oled_big_text(int(player_list[player_move].token), "Do you want to place a bid. One person must say yes per round", 0, 0, 1)
                oled_big_show(int(player_list[player_move].token))
                oled_text(int(player_list[player_move].token), "<-no       yes->", 0, 36, 1)
                oled_show(int(player_list[player_move].token))
                bid = "no"
                while True:
                    if pcf_pin(int(player_list[player_move].token), green) == 0:
                        bid = "yes"
                        time.sleep(.3)
                        break
                    if pcf_pin(int(player_list[player_move].token), yellow) == 0:
                        time.sleep(.3)
                        break
                time.sleep(2)
                oled_big_fill(int(player_list[player_move].token))
                oled_big_show(int(player_list[player_move].token))
                oled_fill(int(player_list[player_move].token))
                oled_show(int(player_list[player_move].token))

            if bid == "yes":
                if auction_price > player_list[player_move].balance:
                    print("You don't have enough money to bid")
                    oled_big_text(int(player_list[player_move].token), "You don't have enough money", 0, 0, 1)
                    oled_big_show(int(player_list[player_move].token))
                    time.sleep(2)
                    oled_big_fill(int(player_list[player_move].token))
                    oled_big_show(int(player_list[player_move].token))
                    bid = "no"
                else:
                    if player_list[player_move].ai == True:
                        auction_bid = auction_price + 50
                    else:
                        auction_bid = 0
                        oled_big_text(int(player_list[player_move].token), "How much to bid?", 0, 0, 1)
                        oled_big_text(int(player_list[player_move].token), f"Current price - ${auction_price}", 0, 15, 1)
                        oled_big_show(int(player_list[player_move].token))
                        while True:
                            oled_big_rect(int(player_list[player_move].token), 0, 45, 128, 60, 0, True)
                            oled_big_text(int(player_list[player_move].token), f"You are bidding {auction_bid}", 0, 45, 1)
                            oled_big_show(int(player_list[player_move].token))
                            # FIX: use player_move's controller, not turn's
                            auction_bid -= encoder(int(player_list[player_move].controller), "delta") * 10
                            if encoder(int(player_list[player_move].controller), "switch") == 0:
                                time.sleep(.3)
                                oled_big_fill(int(player_list[player_move].token))
                                oled_big_text(int(player_list[player_move].token), f"You chose to bid {auction_bid}", 0, 0, 1)
                                oled_big_show(int(player_list[player_move].token))
                                break
                        time.sleep(2)
                        oled_big_fill(int(player_list[player_move].token))
                        oled_big_show(int(player_list[player_move].token))

                    if auction_bid < auction_price:
                        print("You can't bid lower than the current price")
                        oled_big_text(int(player_list[player_move].token), "You can't bid lower than the current price", 0, 0, 1)
                        oled_big_show(int(player_list[player_move].token))
                        time.sleep(2)
                        oled_big_fill(int(player_list[player_move].token))
                        oled_big_show(int(player_list[player_move].token))
                    else:
                        auction_price = auction_bid
                        print(f"The price is now ${auction_price}")
                        oled_big_text(int(player_list[player_move].token), "The price is now", 0, 0, 1)
                        oled_big_text(int(player_list[player_move].token), f"${auction_price}", 0, 15, 1)
                        oled_big_show(int(player_list[player_move].token))
                        time.sleep(2)
                        oled_big_fill(int(player_list[player_move].token))
                        oled_big_show(int(player_list[player_move].token))
            elif bid == "no":
                player_list[player_move].auction = False

        player_move += 1
        time.sleep(2)

        if player_move >= len(player_list):
            player_move = 0
            players_auction = 0
            for i in range(len(player_list)):
                if player_list[i].auction == True:
                    players_auction += 1
                    winner = i

            if players_auction == 1:
                print(f"{player_list[winner].token} has won!")
                oled_big_text(int(player_list[winner].token), f"Player {player_list[winner].token} has won!", 0, 0, 1, all=True)  # FIX: all=True not all==True
                oled_big_show(int(player_list[winner].token), all=True)
                time.sleep(2)
                oled_big_fill(int(player_list[winner].token), all=True)
                oled_big_show(int(player_list[winner].token), all=True)
                player_list[winner].title_deeds.append(name)
                player_list[winner].balance -= auction_price
                update_info(winner)  # FIX: was update_info(turn)
                for i in range(len(player_list)):
                    player_list[i].auction = True
                break

            elif players_auction == 0:
                oled_big_text(int(player_list[0].controller), "Some one must win", 0, 0, 1, all=True)  # FIX: all=True, use index 0 safely
                oled_big_show(int(player_list[0].controller), all=True)
                time.sleep(2)
                oled_big_fill(int(player_list[0].controller), all=True)
                oled_big_show(int(player_list[0].controller), all=True)
                must_win += 1
                for i in range(len(player_list)):
                    player_list[i].auction = True

    return player_list
# function that runs teh auction
"""def auction(player_list, name):
    player_move = 0
    auction_price = 0
    must_win = 0
    print(f"Auction for {name} has started")
    oled_big_text(int(player_list[turn].controller), "Auction for", 0, 0, 1, all = True)
    oled_big_text(int(player_list[turn].controller), name, 0, 15, 1, all = True)
    oled_big_text(int(player_list[turn].controller), "has started", 0, 25, 1, all = True)
    oled_big_show(int(player_list[turn].controller), all = True)
    time.sleep(2)
    oled_big_fill(int(player_list[turn].controller), all = True)
    oled_big_show(int(player_list[turn].controller), all = True)
    for i in range(len(title_deed)):
        if title_deed[i].place == name:
            break
    while True:
        # if the value auction in teh player class is true it runs
        # if teh player ever says no in teh bid, it will not ask tehm again
        if player_list[player_move].auction == True:
            if player_list[player_move].ai == True:
                bid = AI(player_list, "bid", auction_price, i, turn)
                if bid == "no":
                    print("asdf")
                if must_win > 3:
                    bid = "yes"
                    must_win = 0
            else:
                oled_big_text(int(player_list[player_move].token), "Do you want to place a bid. One person must say yes per round", 0, 0, 1)
                oled_big_show(int(player_list[player_move].token))
                oled_text(int(player_list[player_move].token), "<-no       yes->", 0, 36, 1)
                oled_show(int(player_list[player_move].token))
                bid = "no"
                while True:
                    if pcf_pin(int(player_list[player_move].token), green) == 0:
                        bid = "yes"
                        time.sleep(.3)
                        break
                    if pcf_pin(int(player_list[player_move].token), yellow) == 0:
                        time.sleep(.3)
                        break
                time.sleep(2)
                oled_big_fill(int(player_list[player_move].token))
                oled_big_show(int(player_list[player_move].token))
                oled_fill(int(player_list[player_move].token))
                oled_show(int(player_list[player_move].token))
            if bid == "yes":
                if auction_price > player_list[player_move].balance:
                    print("You don't have enough money to bid")
                    oled_big_text(int(player_list[player_move].token), "You don't have enough money", 0, 0, 1)
                    oled_big_show(int(player_list[player_move].token))
                    time.sleep(2)
                    oled_big_fill(int(player_list[player_move].token))
                    oled_big_show(int(player_list[player_move].token))
                    bid = "no"
                else:
                    if player_list[player_move].ai == True:
                        auction_bid = auction_price + 50
                    else:
                        auction_bid = 0
                        oled_big_text(int(player_list[player_move].token), "How much to bid?", 0, 0, 1)
                        oled_big_text(int(player_list[player_move].token), f"Current price - ${auction_price}", 0, 15, 1)
                        oled_big_show(int(player_list[player_move].token))
                        while True:
                            oled_big_rect(int(player_list[player_move].token), 0, 45, 128, 60, 0, True)
                            oled_big_text(int(player_list[player_move].token), f"You are bidding {auction_bid}", 0, 45, 1)
                            oled_big_show(int(player_list[player_move].token))
                            auction_bid -= encoder(int(player_list[turn].controller), "delta" )*10
                            if encoder(int(player_list[turn].controller), "switch" ) == 0:
                                time.sleep(.3)
                                oled_big_fill(int(player_list[player_move].token))
                                oled_big_text(int(player_list[player_move].token), f"You chose to bid {auction_bid}", 0, 0, 1)
                                oled_big_show(int(player_list[player_move].token))
                                break
                        time.sleep(2)
                        oled_big_fill(int(player_list[player_move].token))
                        oled_big_show(int(player_list[player_move].token))
                    if auction_bid < auction_price:
                        print("You can't bid lower than the current price")
                        oled_big_text(int(player_list[player_move].token), "You can't bid lower than the current price", 0, 0, 1)
                        oled_big_show(int(player_list[player_move].token))
                        time.sleep(2)
                        oled_big_fill(int(player_list[player_move].token))
                        oled_big_show(int(player_list[player_move].token))
                    else:
                        auction_price = auction_bid
                        print(f"The price is now ${auction_price}")
                        oled_big_text(int(player_list[player_move].token), "The price is now", 0, 0, 1)
                        oled_big_text(int(player_list[player_move].token), f"${auction_price}", 0, 15, 1)
                        oled_big_show(int(player_list[player_move].token))
                        time.sleep(2)
                        oled_big_fill(int(player_list[player_move].token))
                        oled_big_show(int(player_list[player_move].token))
            elif bid == "no":
                player_list[player_move].auction = False
        player_move += 1
        time.sleep(2)
        # it resets player_move if it is to high
        if player_move >= len(player_list):
            player_move = 0
            players_auction = 0
            # adds one to players_auction for every player that is still bidding
            for i in range(len(player_list)):
                if player_list[i].auction == True:
                    players_auction += 1
                    winner = i
            # if there is only one bidder left, it runs
            if players_auction == 1:
                print(f"{player_list[winner].token} has won!")
                oled_big_text(int(player_list[winner].token), f"Player {player_list[winner].token} has won!", 0, 0, 1, all == True)
                oled_big_show(int(player_list[winner].token), all == True)
                time.sleep(2)
                oled_big_fill(int(player_list[winner].token), all == True)
                oled_big_show(int(player_list[winner].token), all == True)
                # gives the player teh title deed and takes the money away
                player_list[winner].title_deeds.append(name)
                player_list[winner].balance -= auction_price
                update_info(turn)
                # resets the auction value in teh class
                for i in range(len(player_list)):
                    player_list[i].auction = True
                break
            # if everyone says no, it restarts teh auction.
            elif players_auction == 0:
                oled_big_text(int(player_list[player_move].token), "Some one must win", 0, 0, 1, all == True)
                oled_big_show(int(player_list[player_move].token), all == True)
                time.sleep(2)
                oled_big_fill(int(player_list[player_move].token), all == True)
                oled_big_show(int(player_list[player_move].token), all == True)
                must_win += 1
                for i in range(len(player_list)):
                    player_list[i].auction = True
    return player_list"""


# code for the ai
def AI(player_list, action, price, location, turn, reciver=""):
    """
    this ai works by seeing what space it is on
    then the action parameter will tell it what action to do
    each input will have a seperate action
    teh action is kinda like a key, telling teh ai what input it is being asked
    it will take in its current position and others to find teh appropriate move
    if teh ai will have $10 left when buying a title deed, it wont buy it
    but if it will have $200 left over, then it will
    except if multiple players have title deeds with high rent
    then it will buy if it has $500 over
    """
    colorsets = [
        ["Mediterranean Ave", "Baltic Ave"],
        ["Oriental Ave", "Vermont Ave", "Connecticut Ave"],
        ["St. Charles Place", "States Ave", "Virginia Ave"],
        ["St. James Place", "Tennessee Ave", "New York Ave"],
        ["Kentucky Ave", "Indiana Ave", "Illinois Ave"],
        ["Atlantic Ave", "Ventnor Ave", "Marvin Gardens"],
        ["Pacific Ave", "North Carolina Ave", "Pennsylvania Ave"],
        ["Park Place", "Boardwalk"],
    ]
    if action == "bid":
        player_list[turn].title_deeds.append(title_deed[location].place)
        colorset = check_color_set(turn, True)
        player_list[turn].title_deeds.remove(title_deed[location].place)
        if colorset == True:
            return "yes"
        else:
            if num_turn < len(player_list) * 4:
                if location in [9, 10, 11, 12, 13, 14]:
                    if player_list[turn].balance - price > 100:
                        return "yes"
                    else:
                        return "no"
                else:
                    if player_list[turn].balance - price > 150:
                        return "yes"
                    else:
                        return "no"
            else:
                if location in [9, 10, 11, 12, 13, 14]:
                    if player_list[turn].balance - price > 200:
                        return "yes"
                    else:
                        return "no"
                else:
                    if player_list[turn].balance - price > 250:
                        return "yes"
                    else:
                        return "no"
    if action == "sell_t":
        aimort_td = []
        aimort_td_num = []
        aimort_td_value = []
        for i in range(len(player_list[turn].title_deeds)):
            aimort_td_value.append(player_list[turn].title_deeds[i])
            aimort_td_value.append(title_deed[i].calc_sell())
            aimort_td_num.append(title_deed[i].calc_sell())
            aimort_td.append(aimort_td_value)
            aimort_td_value = []
        sorted(aimort_td_num)
        for j in range(len(aimort_td_num)):
            if aimort_td_num[-1] == aimort_td[j][1]:
                sell_t = aimort_td[j][0]
                break
        return sell_t
    if action == "td_to_give":
        while True:
            # lopttd = list_of_possible_trade_td
            lopttd = [i for i in player_list[turn].title_deeds]
            ########
            ai_td = []
            ai_td_num = []
            ai_td_value = []
            for i in range(len(lopttd)):
                ai_td_value.append(lopttd[i])
                ai_td_value.append(title_deed[i].calc_sell())
                ai_td_num.append(title_deed[i].calc_sell())
                ai_td.append(ai_td_value)
                ai_td_value = []
            sorted(ai_td_num)
            for j in range(len(ai_td_num)):
                if ai_td_num[-1] == ai_td[j][1]:
                    trade_t = ai_td[j][0]
                    break
            ########
            for i in range(len(player_list)):
                if reciver == player_list[i].token:
                    break
            player_list[i].title_deeds.append(trade_t)
            colorset = check_color_set(i, True)
            player_list[i].title_deeds.remove(trade_t)
            if colorset == False:
                return trade_t
            else:
                lopttd.remove(trade_t)
    # on property
    if player_list[turn].position in [1, 3, 6, 8, 9, 11, 13, 14, 16, 18, 19, 21, 23, 24, 26, 27, 29, 31, 32, 34, 37, 39]:
        # branch runs if the input is asking to buy a house or hotel
        if action == "buyh":
            if num_turn < len(player_list) * 3:
                return "yes"
            else:
                # if teh amount of turns is more than 25, then it will know it is probobly in endgame
                if num_turn > 25:
                    if (player_list[turn].balance - price) < 400:
                        for loop in range(3):
                            aimort_td = []
                            aimort_td_num = []
                            aimort_td_value = []
                            for i in range(len(player_list[turn].title_deeds)):
                                aimort_td_value.append(player_list[turn].title_deeds[i])
                                aimort_td_value.append(title_deed[i].calc_sell())
                                aimort_td_num.append(title_deed[i].calc_sell())
                                aimort_td.append(aimort_td_value)
                                aimort_td_value = []
                            sorted(aimort_td_num)
                            for j in range(len(aimort_td_num)):
                                if aimort_td_num[-1] == aimort_td[j][1]:
                                    sell_t = aimort_td[j][0]
                                    break
                            for i in range(len(title_deed)):
                                if title_deed[i].place == sell_t:
                                    title_deed[i].mortgage = True
                                    player_list[turn].balance += (
                                        title_deed[i].calc_sell() * 0.5
                                    )
                                    break
                            for i in range(len(train)):
                                if train[i].name == sell_t:
                                    train[i].mortgage = True
                                    player_list[turn].balance += 100
                                    break
                            for i in range(len(utility)):
                                if utility[i].name == sell_t:
                                    utility[i].mortgage = True
                                    player_list[turn].balance += 75
                                    break
                            list_of_td = [
                                title_deed[i].place for i in range(len(title_deed))
                            ]
                            player_list[turn].mortgaged_p.append(sell_t)
                            player_list[turn].title_deeds.remove(sell_t)
                            try:
                                if sell_t in list_of_td[:5]:
                                    player_list[turn].balance += (
                                        50
                                        * title_deed[list_of_td.index(sell_t)].num_house
                                    )
                                    player_list[turn].balance += (
                                        50
                                        * title_deed[list_of_td.index(sell_t)].num_hotel
                                    )
                                elif sell_t in list_of_td[5:11]:
                                    player_list[turn].balance += (
                                        100
                                        * title_deed[list_of_td.index(sell_t)].num_house
                                    )
                                    player_list[turn].balance += (
                                        100
                                        * title_deed[list_of_td.index(sell_t)].num_hotel
                                    )
                                elif sell_t in list_of_td[11:17]:
                                    player_list[turn].balance += (
                                        150
                                        * title_deed[list_of_td.index(sell_t)].num_house
                                    )
                                    player_list[turn].balance += (
                                        150
                                        * title_deed[list_of_td.index(sell_t)].num_hotel
                                    )
                                elif sell_t in list_of_td[17:]:
                                    player_list[turn].balance += (
                                        200
                                        * title_deed[list_of_td.index(sell_t)].num_house
                                    )
                                    player_list[turn].balance += (
                                        200
                                        * title_deed[list_of_td.index(sell_t)].num_hotel
                                    )
                                player_list[turn].house -= title_deed[
                                    list_of_td.index(sell_t)
                                ].num_house
                                player_list[turn].hotel -= title_deed[
                                    list_of_td.index(sell_t)
                                ].num_hotel
                                title_deed[list_of_td.index(sell_t)].num_house = 0
                                title_deed[list_of_td.index(sell_t)].num_hotel = 0
                            except ValueError:
                                pass
                            if player_list[turn].balance > 250:
                                return "yes"
                            else:
                                if loop == 3:
                                    return "no"
                else:
                    return "yes"
        if action == "buyp":

            if num_turn < len(player_list) * 3:
                return "yes"
            if (title_deed[location].place in colorsets[4]) or (
                title_deed[location].place in colorsets[5]
            ):
                if num_turn < 15:
                    if player_list[turn].balance - price > 50:
                        return "yes"
                    else:
                        return "no"
                else:
                    if player_list[turn].balance - price > 150:
                        return "yes"
                    else:
                        return "no"
            else:
                if num_turn < 15:
                    if player_list[turn].balance - price > 10:
                        return "yes"
                    else:
                        return "no"
                else:
                    if player_list[turn].balance - price > 200:
                        return "yes"
                    else:
                        return "no"
    # on special place
    if player_list[turn].position in [0, 10, 20, 30, 4, 38]:
        if action == "payojfc":
            if num_turn > 20:
                if player_list[turn].time_in_jail == 3:
                    return "yes"
                else:
                    return "no"
            else:
                return "yes"
    # on railroad
    if player_list[turn].position in [5, 15, 25, 35]:
        if action == "buyrr":
            if num_turn < len(player_list) * 3:
                return "yes"
            else:
                if player_list[turn].position == 25:
                    if player_list[turn].balance - price > 100:
                        return "yes"
                else:
                    if player_list[turn].balance - price > 150:
                        return "yes"
                return "no"
    # on utility
    if player_list[turn].position in [12, 28]:
        if action == "buyu":
            if num_turn < len(player_list) * 3:
                return "yes"
            else:
                if player_list[turn].position == 28:
                    if player_list[turn].balance - price > 100:
                        return "yes"
                else:
                    if player_list[turn].balance - price > 150:
                        return "yes"
                return "no"


# Creates an 11 by 11 array
visual_board = [["[ ]" for i in range(11)] for i in range(11)]


# Function sets the visual board
def set_board():
    # used to assign each value in teh array
    vb = ["[🔒 10]", "[C 11]", "[💡 12]", "[S 13]", "[V 14]", "[🚂 15]", "[J 16]", "[📦 17]", "[T 18]", "[N 19]", "[🚗 20]", "[C 9]", "                                                    ", " ", " ", " ", " ", " ", " ", " ", " ", "[K 21]", "[V 8]", "                                                   ", " ", " ", " ", " ", " ", " ", " ", " ", "[❓ 22]", "[❓ 7]", "                                                   ", " ", " ", " ", " ", " ", " ", " ", " ", "[I 23]", "[O 6]", "                                                    ", " ", " ", " ", " ", " ", " ", " ", " ", "[I 24]", "[🚂 5]", "                                                  ", " ", " ", " ", " ", " ", " ", " ", " ", "[🚂 25]", "[💰 4]", "                                                   ", " ", " ", " ", " ", " ", " ", " ", " ", "[A 26]", "[B 3]", "                                                    ", " ", " ", " ", " ", " ", " ", " ", " ", "[V 27]", "[📦 2]", "                                                  ", " ", " ", " ", " ", " ", " ", " ", " ", "[🚿 28]", "[M 1]", "                                                    ", " ", " ", " ", " ", " ", " ", " ", " ", "[M 29]", "[➢  0]", "[B 39]", "[💍 38]", "[P 37]", "[❓ 36]", "[🚂 35]", "[P 34]", "[📦 33]", "[N 32]", "[P 31]", "[🚓 30]"]
    a = 0
    # sets the value in teh array
    for i in range(11):
        for j in range(11):
            visual_board[i][j] = vb[a]
            a += 1


set_board()


# prints the visual board
def print_board():
    for i in range(len(visual_board)):
        print("".join([str(x) for x in visual_board[i]]))


board = []

def show_message_to_all(message):
    oled_big_fill(0, all=True)
    oled_big_show(0, all=True)
    oled_big_fill(0, all=True)
    oled_big_text(0, message, 0, 0, 1, all=True)
    oled_big_show(0, all=True)
# makes the board that is used by teh computer to calculate
def make_bts_board():
    # things chooses which title deed goes into the square1F512
    thing = 0
    thing1 = 0
    thing2 = 0
    thing3 = 0
    thing4 = 0
    for i in range(40):
        # makes it so board doesnt go out of range
        board.append(i)
        # places the spot for title deeds
        if i in [1, 3, 6, 8, 9, 11, 13, 14, 16, 18, 19, 21, 23, 24, 26, 27, 29, 31, 32, 34, 37, 39]:
            board[i] = title_deed[thing].place
            thing += 1
        # places the utilities
        if i in [12, 28]:
            board[i] = utility[thing1].name
            thing1 += 1
        # places the community chests
        if i in [2, 17, 33]:
            shuffle(community_chest)
            board[i] = community_chest[thing2].name
            thing2 += 1
        # places chance cards
        if i in [7, 22, 36]:
            shuffle(chance_card)
            board[i] = chance_card[thing3].name
            thing3 += 1
        # places Railroads
        if i in [5, 15, 25, 35]:
            board[i] = train[thing4].name
            thing4 += 1
    # places all teh special places go, jail, etc.
    board[0] = special[0].name
    board[10] = special[1].name
    board[20] = special[2].name
    board[30] = special[3].name
    board[4] = special[4].name
    board[38] = special[5].name
    return board


# makes the moves
turn = 1


def moves(turn_thing):

    # prints ten lines inbetween each turn
    for i in range(10):
        print("")
    # flips between players
    if turn_thing % player_num == 0:
        turn = 0
    elif turn_thing % player_num == 1:
        turn = 1
    elif turn_thing % player_num == 2:
        turn = 2
    elif turn_thing % player_num == 3:
        turn = 3
    elif turn_thing % player_num == 4:
        turn = 4
    else:
        turn = 4
    turn_thing += 1
    ask_save = "no"
    # prints necesarry information
    """
    display these in the mini display
    print(f"It is {player_list[turn].token}'s turn.")
    print(f"You have ${player_list[turn].balance}")
    print(f"You own {player_list[turn].title_deeds}\n")
    print_board()
    """
    time.sleep(2)
    # asks if teh user wants to do an action and calls teh corresponding function
    if not player_list[turn].ai:
        oled_big_fill(int(player_list[turn].controller))

        oled_big_text(int(player_list[turn].controller),"Do you want to: ", 0, 0, 1)
        oled_big_text(int(player_list[turn].controller),"Save Game", 0, 15, 1)
        oled_big_text(int(player_list[turn].controller),"Trade", 0, 25, 1)
        oled_big_text(int(player_list[turn].controller),"Unmortgage", 0, 35, 1)
        oled_big_text(int(player_list[turn].controller),"See Properties", 0, 45, 1)
        oled_big_show(int(player_list[turn].controller))
        oled_text(int(player_list[turn].controller),"<-no       yes->", 0, 46, 1)
        oled_show(int(player_list[turn].controller))
        make_action = "no"
        while True:
            if pcf_pin(int(player_list[turn].controller),green) == 0:
                make_action = "yes"
                time.sleep(.3)
                break
            if pcf_pin(int(player_list[turn].controller),yellow) == 0:
                time.sleep(.3)
                break
        oled_big_fill(int(player_list[turn].controller))
        oled_big_show(int(player_list[turn].controller))
        oled_fill(int(player_list[turn].controller))
        oled_show(int(player_list[turn].controller))
        if make_action == "yes":
            #action_to_make = input("What action do you want to make(save, trade, unmortgage): ")
            oled_big_text(int(player_list[turn].controller),"Which one?: ", 0, 0, 1)
            oled_big_text(int(player_list[turn].controller),"Save Game", 0, 15, 1)
            oled_big_text(int(player_list[turn].controller),"Trade", 0, 25, 1)
            oled_big_text(int(player_list[turn].controller),"Unmortgage", 0, 35, 1)
            oled_big_text(int(player_list[turn].controller),"See Properties", 0, 45, 1)
            oled_big_text(int(player_list[turn].controller),"Quit", 0, 55, 1)
            oled_big_show(int(player_list[turn].controller))
            make_action = "no"
            arrow_loc = 15
            while True:
                oled_big_rect(int(player_list[turn].token), 90, 10, 40, 128, 0, True)
                oled_big_text(int(player_list[turn].controller), "<--", 100, arrow_loc, 1)
                oled_big_show(int(player_list[turn].controller))
                arrow_loc -= encoder(int(player_list[turn].controller), "delta" )*10
                if arrow_loc < 15:
                    arrow_loc = 15
                if arrow_loc > 55:
                    arrow_loc = 55
                if encoder(int(player_list[turn].controller), "switch" ) == 0:
                    time.sleep(.3)
                    break
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
            if arrow_loc == 55:
                None
            if arrow_loc == 45:
                oled_big_text(int(player_list[turn].controller), "Your Title Deeds", 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                tds_owned = len(player_list[turn].title_deeds)
                td_to_show = 0
                while True:
                    oled_big_rect(int(player_list[turn].controller), 0, 15, 128, 30, 0, True)
                    oled_big_text(int(player_list[turn].controller), player_list[turn].title_deeds[td_to_show], 0, 15, 1)
                    type_of_td = ""
                    for i in range(len(title_deed)):
                        if title_deed[i].place == player_list[turn].title_deeds[td_to_show]:
                            type = "title deed"
                            break
                    for i in range(len(train)):
                        if train[i].name == player_list[turn].title_deeds[td_to_show]:
                            type = "train"
                            break
                    for i in range(len(utility)):
                        if utility[i].name == player_list[turn].title_deeds[td_to_show]:
                            type = "utility"
                            break
                    if type == "title deed":
                        oled_big_text(int(player_list[turn].controller), f"{title_deed[i].num_house} houses", 0, 45, 1)
                        oled_big_text(int(player_list[turn].controller), f"{title_deed[i].num_hotel} hotels", 0, 55, 1)
                        oled_big_text(int(player_list[turn].controller), f"Rent: ${title_deed[i].rent}", 0, 65, 1)
                        if title_deed[i].mortgage:
                            oled_big_text(int(player_list[turn].controller), "Mortgaged", 0, 75, 1)
                        if title_deed[i].colorset:
                            oled_big_text(int(player_list[turn].controller), "Part of Color Set", 0, 85, 1)
                    if type == "train":
                        if train[i].mortgage:
                            oled_big_text(int(player_list[turn].controller), "Mortgaged", 0, 45, 1)
                    if type == "utility":
                        if utility[i].mortgage:
                            oled_big_text(int(player_list[turn].controller), "Mortgaged", 0, 45, 1)

                    oled_big_show(int(player_list[turn].controller))
                    td_to_show += encoder(int(player_list[turn].controller), "delta" )
                    if td_to_show < 0:
                        td_to_show = tds_owned-1
                    if td_to_show > tds_owned-1:
                        td_to_show = 0
                    if encoder(int(player_list[turn].controller), "switch" ) == 0:
                        break
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))
            if arrow_loc == 15:
                while True:
                    print(save_files)
                    oled_big_text(int(player_list[turn].controller),"Which save file", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    save_name = 1
                    while True:
                        oled_big_rect(int(player_list[turn].token), 0, 15, 20, 30, 0, True)
                        oled_big_text(int(player_list[turn].controller), str(save_name), 0, 15, 1)
                        oled_big_show(int(player_list[turn].controller))
                        save_name += encoder(int(player_list[turn].controller), "delta" )
                        if save_name < 1:
                            save_name = 1
                        if save_name > 10:
                            save_name = 10
                        if encoder(int(player_list[turn].controller), "switch" ) == 0:
                            save_name = str(save_name)
                            time.sleep(.3)
                            break
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    if save_name in save_files:
                        oled_big_text(int(player_list[turn].controller),"You already have a save there. Do you want to overwite save?", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        oled_text(int(player_list[turn].controller),"<-no       yes->", 0, 46, 1)
                        oled_show(int(player_list[turn].controller))
                        over_write_save = False
                        while True:
                            if pcf_pin(int(player_list[turn].controller),green) == 0:
                                over_write_save = True
                                time.sleep(.3)
                                break
                            if pcf_pin(int(player_list[turn].controller),yellow) == 0:
                                time.sleep(.3)
                                break
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                        oled_fill(int(player_list[turn].controller))
                        oled_show(int(player_list[turn].controller))
                        if over_write_save:
                            oled_big_text(int(player_list[turn].controller),"Saved Successfully", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            save(save_name)
                            save_files.append(save_name)
                            break
                    else:
                        oled_big_text(int(player_list[turn].controller),"Saved Successfully", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        save(save_name)
                        save_files.append(save_name)
                        break
                    sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
            if arrow_loc == 25:
                list_of_players = []
                for i in range(len(player_list)):
                    list_of_players.append(player_list[i].token)
                while True:
                    list_of_tradable_players = []
                    for i in range(len(list_of_players)):
                        if player_list[i].token != player_list[turn].token:
                            list_of_tradable_players.append(player_list[i].token)
                    print(list_of_tradable_players)
                    oled_big_text(int(player_list[turn].controller), "Players to trade with", 0, 0, 1)
                    oled_big_text(int(player_list[turn].controller), str(list_of_tradable_players), 0, 25, 1)
                    oled_big_show(int(player_list[turn].controller))
                    time.sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    #trade_to = input("Who recives the card?: ")
                    oled_big_text(int(player_list[turn].controller), "Who recives the card?", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    trade_player_num = len(list_of_tradable_players)
                    player_to_show = 0
                    while True:
                        oled_rect(int(player_list[turn].controller), 0, 36, 128, 10, 0, True)
                        oled_text(int(player_list[turn].controller), list_of_tradable_players[player_to_show], 0, 36, 1)
                        oled_show(int(player_list[turn].controller))
                        player_to_show += encoder(int(player_list[turn].controller), "delta" )
                        if player_to_show < 0:
                            player_to_show = trade_player_num-1
                        if player_to_show > trade_player_num-1:
                            player_to_show = 0
                        if encoder(int(player_list[turn].controller), "switch" ) == 0:
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_text(int(player_list[turn].controller), "You chose to give", 0, 0, 1)
                            oled_big_text(int(player_list[turn].controller), list_of_tradable_players[player_to_show], 0, 15, 1)
                            oled_big_show(int(player_list[turn].controller))
                            trade_to = list_of_tradable_players[player_to_show]
                            break
                    time.sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    oled_fill(int(player_list[turn].controller))
                    oled_show(int(player_list[turn].controller))
                    if trade_to in list_of_players:
                        break
                    else:
                        print("Type a valid input")
                        time.sleep(2)
                broke(turn, trade_to, player_list, True)
            elif arrow_loc == 35:
                unmort_p = []
                for i in range(len(player_list)):
                    if title_deed[i].mortgage == True:
                        unmort_p.append(title_deed[i])
                while True:
                    print(unmort_p)
                    #unmort = input("What property do you want to unmortgage?: ")
                    oled_big_text(int(player_list[turn].controller), "What property do you want to unmortgage?", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    tds_mort = len(player_list[turn].mortgaged_p)
                    td_to_show = 0
                    while True:
                        oled_rect(int(player_list[turn].controller), 0, 36, 128, 10, 1, True)
                        oled_text(int(player_list[turn].controller), player_list[turn].mortgaged_p[td_to_show], 0, 36, 1)
                        oled_show(int(player_list[turn].controller))
                        td_to_show += encoder(int(player_list[turn].controller), "delta" )
                        if td_to_show < 0:
                            td_to_show = tds_mort-1
                        if td_to_show > tds_mort-1:
                            td_to_show = 0
                        if encoder(int(player_list[turn].controller), "switch" ) == 0:
                            oled_big_text(int(player_list[turn].controller), "You chose to unmortgage", 0, 0, 1)
                            oled_big_text(int(player_list[turn].controller), player_list[turn].mortgaged_p[td_to_show], 0, 15, 1)
                            oled_big_show(int(player_list[turn].controller))
                            unmort = player_list[turn].mortgaged_p[td_to_show]
                            break
                    time.sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    oled_fill(int(player_list[turn].controller))
                    oled_show(int(player_list[turn].controller))
                    try:
                        if (
                            unmort_p[unmort_p.index(unmort)].buy * 0.1
                            > player_list[turn].balance
                        ):
                            print("You don't have enough money to unmortgage it")
                            oled_big_text(int(player_list[turn].controller), "You don't have enough money to unmortgage it", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                        else:
                            title_deed[unmort_p.index(unmort)].mortgage = False
                            player_list[turn].title_deed.append(unmort)
                            player_list[turn].mortgaged_p.remove(unmort)
                            player_list[turn].balance -= (
                                unmort_p[unmort_p.index(unmort)].buy * 1.1
                            )
                            update_info(turn)
                            time.sleep(2)
                        break
                    except IndexError:
                        print("Type a valid input")
                        time.sleep(2)
    save_file("save_file_of_save_files.txt", save_files)
    ##########
    player_list[turn].title_deeds = list(set(player_list[turn].title_deeds))
    # rolls dice
    # I need two dice because when leaving jail, both dice need ot be the same.
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    dice = dice1 + dice2
    oled_big_fill(player_list[0].controller, all=True)
    oled_big_text(player_list[0].controller, f"Its player {turn+1}'s turn", 0, 0, 1, all=True)
    oled_big_show(player_list[0].controller, all=True)
    if not player_list[turn].ai:
        oled_big_fill(int(player_list[turn].controller))

        oled_big_fill(int(player_list[turn].controller))
        oled_big_show(int(player_list[turn].controller))
        if int(player_list[turn].controller) == 1:
            oled = oled_big1
        if int(player_list[turn].controller) == 2:
            oled = oled_big2
        if int(player_list[turn].controller) == 3:
            oled = oled_big3
        if int(player_list[turn].controller) == 4:
            oled = oled_big4
        roll_dice(oled, dice, 35, 35, 50, 50)
        time.sleep(2)
        oled_big_fill(int(player_list[turn].controller))
        oled_big_show(int(player_list[turn].controller))
    if player_list[turn].jail != True:
        copyofpos = player_list[turn].position
        while True:
            player_list[turn].position = copyofpos + dice

            collision = False
            for i in player_list:
                if (i.position == player_list[turn].position and i.token != player_list[turn].token) or (player_list[turn].position == 30 and i.position == 10):
                    collision = True
                    if dice != 12:
                        dice += 1
                    else:
                        dice = 2
                    break

            if not collision:
                break


        oled_big_fill(player_list[0].controller, all=True)
        oled_big_text(player_list[0].controller, f"Player {turn+1} rolled a {dice}", 0, 0, 1, all=True)
        oled_big_show(player_list[0].controller, all=True)
        # used to make the print statement grammaticly correct

        
        # used to move the corresponding moves if it passes go
        if player_list[turn].position > 39:
            player_list[turn].position -= 40
        update_info(turn)
        move_player(copyofpos, player_list[turn].position)
        oled_big_fill(int(player_list[turn].controller), all=True)
        oled_big_show(int(player_list[turn].controller), all=True)
        print(f"You are on square {player_list[turn].position}")
        oled_big_fill(player_list[0].controller, all=True)
        oled_big_text(player_list[0].controller, f"Player {turn+1} landed on square {player_list[turn].position}", 0, 0, 1, all=True)
        oled_big_show(player_list[0].controller, all=True)
        if not player_list[turn].ai:
            oled_big_fill(int(player_list[turn].controller))

            oled_big_fill(player_list[turn].controller)
            oled_big_text(int(player_list[turn].controller),"You landed on", 0, 0, 1)
            oled_big_text(int(player_list[turn].controller),"square:", 0,15,1)
            oled_big_text(int(player_list[turn].controller), str(player_list[turn].position), 0, 25, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(2)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
        oled_big_fill(player_list[0].controller, all=True)
        oled_big_show(player_list[0].controller, all=True)
        # sees if teh player passes go and gives $200
        if (
            copyofpos > 27
            and (player_list[turn].position >= 0 and player_list[turn].position < 12)
        ) or player_list[turn].position == 0:
            print("You past Go. You got $200")
            if not player_list[turn].ai:
                oled_big_fill(int(player_list[turn].controller))

                oled_big_text(int(player_list[turn].controller), "You passed go", 0, 0, 1)
                oled_big_text(int(player_list[turn].controller), "You got $200", 0, 15, 1)
                oled_big_show(int(player_list[turn].controller))
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))
            player_list[turn].balance += 200
            update_info(turn)
            
    check_color_set(turn)
    return player_list, turn, dice, dice1, dice2


# ilotd = if land on title deed
def ilotd():
    # function for possible actions when landing on a property
    def property_land(place, location, player_list, title_deed):
        location -= 1
        if title_deed[location].mortgage != True:
            thing = True
            # makes a list of all owned title deeds
            list_of_owned_td = []
            for z in range(len(player_list)):
                for y in range(len(player_list[z].title_deeds)):
                    list_of_owned_td.append(player_list[z].title_deeds[y])
            if place in list_of_owned_td:
                # if teh property is owned but not by teh player whos turn it is
                if not (place in player_list[turn].title_deeds):
                    print(
                        f"You must pay rent on {place}/nRent is ${title_deed[location].calc_rent()}."
                    )
                    if not player_list[turn].ai:
                        oled_big_fill(int(player_list[turn].controller))

                        oled_big_text(int(player_list[turn].controller), f"You must pay rent on {str(place)} Rent is ${title_deed[location].calc_rent()}", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        time.sleep(2)
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                    rent_to_pay = title_deed[location].calc_rent()
                    # doubles rent if it is a colorset
                    if title_deed[location].colorset == True:
                        rent_to_pay = (title_deed[location].calc_rent()) * 2
                    player_list[turn].balance -= rent_to_pay
                    update_info(turn)
                    if player_list[turn].balance < 0:
                        player_list = broke(turn, 1, player_list, False)
                    # gives teh rent to teh person who owns teh title deed
                    for j in range(len(player_list)):
                        if place in list_of_owned_td and j != turn:
                            for x in range(len(player_list)):
                                if place in player_list[x].title_deeds:
                                    player_list[x].balance += rent_to_pay
                                    update_info(turn)

                    return player_list
                else:
                    # if teh player owns teh title deed, they can buy a house or hotel
                    buyh = "no"

                    if player_list[turn].ai == True:
                        buyh = AI(
                            player_list,
                            "buyh",
                            title_deed[location].house_buy,
                            location,
                            turn,
                        )
                    else:
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            oled_big_text(int(player_list[turn].controller), "Want to buy a ", 0, 0, 1)
                            oled_big_text(int(player_list[turn].controller), "house or a hotel", 0, 15, 1)
                            oled_big_show(int(player_list[turn].controller))
                            oled_text(int(player_list[turn].controller), "<-no       yes->", 0, 36, 1)
                            oled_show(int(player_list[turn].controller))
                            buyh = "no"
                            while True:
                                if pcf_pin(int(player_list[turn].controller), green) == 0:
                                    buyh = "yes"
                                    time.sleep(.3)
                                    break
                                if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                                    time.sleep(.3)
                                    break
                            oled_fill(int(player_list[turn].controller))
                            oled_show(int(player_list[turn].controller))
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                    if title_deed[location].colorset == False and buyh == "yes":
                        print(
                            "You need to own the color set for this title deed before you can buy a house or a hotel"
                        )
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            oled_big_text(int(player_list[turn].controller), "You need to own the color set for this title deed before you can buy a house or a hotel", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(3)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                        return player_list
                    if buyh == "yes":
                        if player_list[turn].balance < title_deed[location].house_buy:
                            print("You don't have enough money")
                            if not player_list[turn].ai:
                                oled_big_fill(int(player_list[turn].controller))

                                oled_big_text(int(player_list[turn].controller), "You dont have enough money", 0, 0, 1)
                                oled_big_show(int(player_list[turn].controller))
                                time.sleep(2)
                                oled_big_fill(int(player_list[turn].controller))
                                oled_big_show(int(player_list[turn].controller))
                            return player_list
                        hotel_or_house = "no"
                        if player_list[turn].ai != True:
                            if not player_list[turn].ai:
                                oled_big_fill(int(player_list[turn].controller))

                                oled_rect(0, 26, 128, 20, 0, True)
                                oled_text(int(player_list[turn].controller), "<-house  hotel->", 0, 36, 1)
                                oled_show(int(player_list[turn].controller))
                                oled_big_text(int(player_list[turn].controller), "House or Hotel", 0, 0, 1)
                                oled_big_show(int(player_list[turn].controller))
                                while True:
                                    if pcf_pin(int(player_list[turn].controller), green) == 0:
                                        hotel_or_house = "hotel"
                                        time.sleep(.3)
                                        break
                                    if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                                        hotel_or_house = "house"
                                        time.sleep(.3)
                                        break
                                oled_big_fill(int(player_list[turn].controller))
                                oled_big_show(int(player_list[turn].controller))
                                oled_fill(int(player_list[turn].controller))
                                oled_show(int(player_list[turn].controller))
                        if hotel_or_house == "house" or (player_list[turn].ai == True):
                            # if teh player has 4 houses, it asks if they want a hotel instead
                            if title_deed[location].num_house == 4:
                                if player_list[turn].ai != True:
                                    if not player_list[turn].ai:
                                        oled_big_fill(int(player_list[turn].controller))

                                        oled_big_text(int(player_list[turn].controller), "You have the max # of houses. Want to buy a hotel instead?", 0, 0, 1)
                                        oled_big_show(int(player_list[turn].controller))
                                        oled_text(int(player_list[turn].controller), "<-no       yes->", 0, 36, 1)
                                        oled_show(int(player_list[turn].controller))
                                        buyh = "no"
                                        while True:
                                            if pcf_pin(int(player_list[turn].controller), green) == 0:
                                                buyh = "yes"
                                                time.sleep(.3)
                                                break
                                            if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                                                time.sleep(.3)
                                                break
                                        time.sleep(2)
                                        oled_big_fill(int(player_list[turn].controller))
                                        oled_big_show(int(player_list[turn].controller))
                                        oled_fill(int(player_list[turn].controller))
                                        oled_show(int(player_list[turn].controller))
                                if buyh == "yes":
                                    hotel_or_house = "hotel"
                            else:
                                print("You bought a house")
                                show_message_to_all(f"player {player_list[turn].token} bought a house on {place}")
                                if not player_list[turn].ai:
                                    oled_big_fill(int(player_list[turn].controller))

                                    
                                    oled_big_text(int(player_list[turn].controller), "You bought a house", 0, 0, 1)
                                    oled_big_show(int(player_list[turn].controller))
                                    time.sleep(2)
                                    oled_big_fill(int(player_list[turn].controller))
                                    oled_big_show(int(player_list[turn].controller))
                                # adds a house
                                title_deed[location].num_house += 1
                                player_list[turn].balance -= title_deed[
                                    location
                                ].house_buy
                                update_info(turn)
                                player_list[turn].house += 1
                        if hotel_or_house == "hotel":
                            if title_deed[location].num_house != 4:
                                print(
                                    "You need four houses on the property until you can buy a hotel"
                                )
                                if not player_list[turn].ai:
                                    oled_big_fill(int(player_list[turn].controller))

                                    oled_big_text(int(player_list[turn].controller), "You need four houses until you can buy a hotel", 0, 0, 1)
                                    oled_big_show(int(player_list[turn].controller))
                                    time.sleep(2)
                                    oled_big_fill(int(player_list[turn].controller))
                                    oled_big_show(int(player_list[turn].controller))
                            elif title_deed[location].num_hotel >= 1:
                                if not player_list[turn].ai:
                                    oled_big_fill(int(player_list[turn].controller))

                                    oled_big_text(int(player_list[turn].controller), "You already have a hotel", 0, 0, 1)
                                    oled_big_show(int(player_list[turn].controller))
                                    time.sleep(2)
                                    oled_big_fill(int(player_list[turn].controller))
                                    oled_big_show(int(player_list[turn].controller))
                            else:
                                show_message_to_all(f"player {player_list[turn].token} bought a hotel on {place}")
                                if not player_list[turn].ai:
                                    oled_big_fill(int(player_list[turn].controller))

                                    
                                    oled_big_text(int(player_list[turn].controller), "You bought a hotel", 0, 0, 1)
                                    oled_big_show(int(player_list[turn].controller))
                                    time.sleep(2)
                                    oled_big_fill(int(player_list[turn].controller))
                                    oled_big_show(int(player_list[turn].controller))
                                # gives them a hotel and removes the hosues
                                title_deed[location].num_hotel += 1
                                player_list[turn].balance -= title_deed[
                                    location - 1
                                ].hotel_buy
                                player_list[turn].house -= 4
                                player_list[turn].hotel += 1
                                update_info(turn)
                return player_list
            else:
                # if teh title deed is not owned, they can buy it
                buyp = "no"
                if player_list[turn].ai == True:
                    buyp = AI(
                        player_list, "buyp", title_deed[location].buy, location, turn
                    )
                if player_list[turn].ai != True:
                    oled_big_text(int(player_list[turn].controller), "Want to buy", 0, 0, 1)
                    oled_big_text(int(player_list[turn].controller), place, 0, 15, 1)
                    oled_big_text(int(player_list[turn].controller), "$" + str(title_deed[location].buy), 0, 45, 1)
                    oled_big_show(int(player_list[turn].controller))
                    oled_text(int(player_list[turn].controller), "<-no       yes->", 0, 36, 1)
                    oled_show(int(player_list[turn].controller))
                    buyp = "no"
                    while True:
                        if pcf_pin(int(player_list[turn].controller), green) == 0:
                            buyp = "yes"
                            time.sleep(.3)
                            break
                        if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                            time.sleep(.3)
                            break
                    time.sleep(1)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    oled_fill(int(player_list[turn].controller))
                    oled_show(int(player_list[turn].controller))
                if buyp == "yes":
                    if player_list[turn].balance < title_deed[location].buy:
                        print("You don't have enough money")
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            oled_big_text(int(player_list[turn].controller), "You dont have enough money", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                    else:
                        print(f"You bought {place}")
                        show_message_to_all(f"player {player_list[turn].token} bought {place}")
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            oled_big_text(int(player_list[turn].controller), "You bought", 0, 0, 1)
                            oled_big_text(int(player_list[turn].controller), place, 0, 15, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                        player_list[turn].title_deeds.append(place)
                        player_list[turn].balance -= title_deed[location].buy
                        update_info(turn)
                else:
                    # auctions off teh title deed if tehy dont want it
                    print(f"{place} is being auctioned off")
                    if not player_list[turn].ai:
                        oled_big_fill(int(player_list[turn].controller))

                        oled_big_text(int(player_list[turn].controller), place, 0, 0, 1)
                        oled_big_text(int(player_list[turn].controller), "is being auctioned off", 0, 15, 1)
                        oled_show(int(player_list[turn].controller))
                        time.sleep(2)
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                    player_list = auction(player_list, place)
                # checks if they player has a colorset after buying the property
                title_deed, player_list = check_color_set(turn)
                return player_list
        else:
            print("You landed on a property that is mortgaged. Lucky you.")
            if not player_list[turn].ai:
                oled_big_fill(int(player_list[turn].controller))

                oled_big_text(int(player_list[turn].controller), "You landed on a mortgaged property. Lucky you", 0, 0, 1)
                oled_show(int(player_list[turn].controller))
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))
        return player_list

    # it firsts looks what color the player is on and then the property
    # brown
    if player_list[turn].position in [1, 3]:
        if player_list[turn].position == 1:
            property_land("Mediterranean Ave", 1, player_list, title_deed)
            return player_list
        if player_list[turn].position == 3:
            property_land("Baltic Ave", 2, player_list, title_deed)
            return player_list
        return player_list
    # light blue
    if player_list[turn].position in [6, 8, 9]:
        if player_list[turn].position == 6:
            property_land("Oriental Ave", 3, player_list, title_deed)
            return player_list
        if player_list[turn].position == 8:
            property_land("Vermont Ave", 4, player_list, title_deed)
            return player_list
        if player_list[turn].position == 9:
            property_land("Connecticut Ave", 5, player_list, title_deed)
            return player_list
        return player_list
    # pink
    if player_list[turn].position in [11, 13, 14]:
        if player_list[turn].position == 11:
            property_land("St. Charles Place", 6, player_list, title_deed)
            return player_list
        if player_list[turn].position == 13:
            property_land("States Ave", 7, player_list, title_deed)
            return player_list
        if player_list[turn].position == 14:
            property_land("Virginia Ave", 8, player_list, title_deed)
            return player_list
        return player_list
    # orange
    if player_list[turn].position in [16, 18, 19]:
        if player_list[turn].position == 16:
            property_land("St. James Place", 9, player_list, title_deed)
            return player_list
        if player_list[turn].position == 18:
            property_land("Tennessee Ave", 10, player_list, title_deed)
            return player_list
        if player_list[turn].position == 19:
            property_land("New York Ave", 11, player_list, title_deed)
            return player_list
        return player_list
    # red
    if player_list[turn].position in [21, 23, 24]:
        if player_list[turn].position == 21:
            property_land("Kentucky Ave", 12, player_list, title_deed)
            return player_list
        if player_list[turn].position == 23:
            property_land("Indiana Ave", 13, player_list, title_deed)
            return player_list
        if player_list[turn].position == 24:
            property_land("Illinois Ave", 14, player_list, title_deed)
            return player_list
        return player_list
    # yellow
    if player_list[turn].position in [26, 27, 29]:
        if player_list[turn].position == 26:
            property_land("Atlantic Ave", 15, player_list, title_deed)
            return player_list
        if player_list[turn].position == 27:
            property_land("Ventnor Ave", 16, player_list, title_deed)
            return player_list
        if player_list[turn].position == 29:
            property_land("Marvin Gardens", 17, player_list, title_deed)
            return player_list
        return player_list
    # green
    if player_list[turn].position in [31, 32, 34]:
        if player_list[turn].position == 31:
            property_land("Pacific Ave", 18, player_list, title_deed)
            return player_list
        if player_list[turn].position == 32:
            property_land("North Carolina Ave", 19, player_list, title_deed)
            return player_list
        if player_list[turn].position == 34:
            property_land("Pennsylvania Ave", 20, player_list, title_deed)
            return player_list
        return player_list
    # blue
    if player_list[turn].position in [37, 39]:
        if player_list[turn].position == 37:
            property_land("Park Place", 21, player_list, title_deed)
            return player_list
        if player_list[turn].position == 39:
            property_land("Boardwalk", 22, player_list, title_deed)
            return player_list
        return player_list


# ilocc=if land on chance card/community chest
def ilocc():
    def check_if_player_there(position):
        for i in player_list:
            if i.position == position:
                return True
        return False
    # see whether it is a chance or community chest
    # chest
    if player_list[turn].position in [2, 17, 33]:
        # picks a card if they land on a space with commynity chest
        print("You landed on community chest")
        chest_card = random.choice(community_chest)
        print(chest_card.name)
        
        show_message_to_all(f"player {player_list[turn].token} landed on a community chest card")
        if not player_list[turn].ai:
            oled_big_fill(int(player_list[turn].controller))

            oled_big_text(int(player_list[turn].controller), "You landed on community chest", 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(1.5)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_text(int(player_list[turn].controller), chest_card.name, 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(3)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
        # does special action if needed
        player_list[turn].balance += chest_card.money
        bypass = False
        if chest_card.jail_card == True:
            player_list[turn].jail_card = True
        if chest_card.place == "Go":
            if check_if_player_there(0):
                bypass = True
            player_list[turn].position = 0
            move_player(player_list[turn].position, 0)
            update_info(turn)
        if chest_card.place == "Jail":
            if check_if_player_there(10):
                bypass = True
            player_list[turn].position = 10
            player_list[turn].jail = True
            move_player(player_list[turn].position, 10)
            update_info(turn)
        if chest_card.place == "get_50" or bypass:
            for i in range(len(player_list)):
                if i == turn:
                    continue
                player_list[i].balance -= 50
                update_info(i)
    # chance
    if player_list[turn].position in [7, 22, 36]:
        # same thing but with chance cards
        print("You landed on chance card")
        chance = random.choice(chance_card)
        print(chance.name)
        
        show_message_to_all(f"player {player_list[turn].token} landed on a chance card")
        if not player_list[turn].ai:
            oled_big_fill(int(player_list[turn].controller))

            oled_big_text(int(player_list[turn].controller), "You landed on a chance card", 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(1.5)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_text(int(player_list[turn].controller), chance.name, 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(3)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
        player_list[turn].balance += chance.money
        if chance.jail_card == True:
            player_list[turn].jail_card = True
        bypass = False
        # moves player if it tells tehm to move to a title deed
        if chance.place == "St. Charles":
            if check_if_player_there(11):
                bypass = True
            move_player(player_list[turn].position, 11)
            player_list[turn].position = 11
            
            update_info(turn)
            
        if chance.place == "Train Station":
            if check_if_player_there(15):
                bypass = True
            move_player(player_list[turn].position, 15)
            player_list[turn].position = 15
            update_info(turn)
            
        if chance.place == "Illinois Ave":
            if check_if_player_there(24):
                bypass = True
            move_player(player_list[turn].position, 24)
            player_list[turn].position = 24
            update_info(turn)
            
        if chance.place == "Go":
            if check_if_player_there(0):
                bypass = True
            move_player(player_list[turn].position, 0)
            player_list[turn].position = 0
            update_info(turn)
            
        if chance.place == "Placeholder for nearest utility":
            # moves player to nearest utility
            if player_list[turn].position == 7:
                if check_if_player_there(12):
                    bypass = True
                move_player(player_list[turn].position, 12)
                player_list[turn].position = 12
                move_player(player_list[turn].position, 12)
            else:
                if check_if_player_there(28):
                    bypass = True
                move_player(player_list[turn].position, 28)
                player_list[turn].position = 28
                
            update_info(turn)
        if chance.place == "Jail":
            if check_if_player_there(10):
                bypass = True
            move_player(player_list[turn].position, 10)
            player_list[turn].position = 10
            player_list[turn].jail = True
            update_info(turn)
            
        if chance.place == "Boardwalk":
            if check_if_player_there(39):
                bypass = True
            move_player(player_list[turn].position, 39)
            player_list[turn].position = 39
            update_info(turn)
            
        if chance.place == "placeholder for player position minus 3 spaces":
            if check_if_player_there(player_list[turn].position - 3):
                bypass = True
            move_player(player_list[turn].position, player_list[turn].position-3, backwards = True)
            player_list[turn].position = player_list[turn].position - 3
            update_info(turn)
            
        if chance.place == "Placeholder for nearest railroad":
            # same thing as utility but with railroads
            if player_list[turn].position == 7:
                if check_if_player_there(15):
                    bypass = True
                move_player(player_list[turn].position, 15)
                player_list[turn].position = 15
                
            if player_list[turn].position == 22:
                if check_if_player_there(25):
                    bypass = True
                move_player(player_list[turn].position, 25)
                player_list[turn].position = 25
                
            if player_list[turn].position == 36:
                if check_if_player_there(5):
                    bypass = True
                move_player(player_list[turn].position, 5)
                player_list[turn].position = 5
                
            update_info(turn)
        if chance.place == "pay_50" or bypass:
            for i in range(len(player_list)):
                if i == turn:
                    continue
                player_list[i].balance += 50
                update_info(i)
    update_info(turn)
    return player_list


# ilosp=if land on special place
# speacial place - jail, free parking, income and luxury tax
def ilosp(player_list):
    if player_list[turn].position == 10:
        if player_list[turn].jail != True:
            print("You are visiting jail")
            if not player_list[turn].ai:
                oled_big_fill(int(player_list[turn].controller))

                show_message_to_all(f"player {player_list[turn].token} is visiting jail")
                oled_big_text(int(player_list[turn].controller), "You are visiting jail", 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))
        else:
            # runs if they are in jail
            print("You are in jail")
            if not player_list[turn].ai:
                oled_big_fill(int(player_list[turn].controller))

                show_message_to_all(f"player {player_list[turn].token} is in jail")
                oled_big_text(int(player_list[turn].controller), "You are in jail", 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))
            jail_input = True
            if dice1 == dice2:
                print("You rolled the same number on each dice!")
                if not player_list[turn].ai:
                    oled_big_fill(int(player_list[turn].controller))

                    show_message_to_all(f"player {player_list[turn].token} rolled the same number on each dice and got out of jail")
                    oled_big_text(int(player_list[turn].controller), "You rolled the same number on each dice!", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    time.sleep(2)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                player_list[turn].jail = False
                jail_input = False

            payojfc = "no"
            # allows teh player to get out of jail
            if player_list[turn].ai == True and jail_input == True:
                payojfc = AI(player_list, "payojfc", 50, 0, turn)
            if player_list[turn].ai != True and jail_input == True:
                oled_big_text(int(player_list[turn].controller), "Do you want to use your get out of jail free card or pay $50", 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                oled_text(int(player_list[turn].controller), "<-no       yes->", 0, 36, 1)
                oled_show(int(player_list[turn].controller))
                payojfc = "no"
                while True:
                    if pcf_pin(int(player_list[turn].controller), green) == 0:
                        payojfc = "yes"
                        time.sleep(.3)
                        break
                    if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                        time.sleep(.3)
                        break
                time.sleep(1)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))
                oled_fill(int(player_list[turn].controller))
                oled_show(int(player_list[turn].controller))
            if not (
                (payojfc == "yes" or player_list[turn].ai == True)
                and jail_input == True
            ):
                if player_list[turn].time_in_jail == 3:
                    print(
                        "You have been in jail for too long. You must pay $50 for use your get out of jail free card"
                    )
                    if not player_list[turn].ai:
                        oled_big_fill(int(player_list[turn].controller))

                        oled_big_text(int(player_list[turn].controller), "You have been in jail for too long. You must pay $50 or use your get out of jail card", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        time.sleep(2)
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                    payojfc = "yes"
                else:
                    player_list[turn].time_in_jail += 1
            if (
                payojfc == "yes" or player_list[turn].ai == True
            ) and jail_input == True:
                if player_list[turn].jail_card == False:
                    if player_list[turn].balance < 50:
                        print(
                            "You don't have a get out of jail free card nor do you have enough money"
                        )
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            oled_big_text(int(player_list[turn].controller), "You don't have a get out of jail free card nor enough money", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                    else:
                        print("You paid $50")
                        show_message_to_all(f"player {player_list[turn].token} paid $50 to get out of jail")
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            
                            oled_big_text(int(player_list[turn].controller), "You paid $50", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                        player_list[turn].jail = False
                        player_list[turn].balance -= 50
                        player_list[turn].time_in_jail = 0
                        update_info(turn)
                else:
                    print("You used your get out of jail free card.")
                    show_message_to_all(f"player {player_list[turn].token} used their get out of jail free card")
                    if not player_list[turn].ai:
                        oled_big_fill(int(player_list[turn].controller))

                        
                        oled_big_text(int(player_list[turn].controller), "You used your get out of jail free card", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        time.sleep(2)
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                    player_list[turn].jail = False
                    player_list[turn].jail_card = False
                    player_list[turn].time_in_jail = 0
    # does teh action based on place that is landed
    if player_list[turn].position == 20:
        print("You are in free parking")
        
        show_message_to_all(f"player {player_list[turn].token} is in free parking")
        if not player_list[turn].ai:
            oled_big_fill(int(player_list[turn].controller))

            oled_big_text(int(player_list[turn].controller), "You are in free parking", 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(2)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
        player_list[turn].jail = False
        player_list[turn].jail_card = False
        player_list[turn].time_in_jail = 0
    if player_list[turn].position == 30:
        print("Go to jail")
        
        show_message_to_all(f"player {player_list[turn].token} is going to jail")
        if not player_list[turn].ai:
            oled_big_fill(int(player_list[turn].controller))

            oled_big_text(int(player_list[turn].controller), "Go to jail", 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(2)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
        player_list[turn].jail = False
        player_list[turn].jail_card = False
        player_list[turn].time_in_jail = 0
        player_list[turn].jail = True
        move_player(player_list[turn].position, 10)
        player_list[turn].position = 10
        update_info(turn)
    if player_list[turn].position == 4:
        print("Pay income tax of $200")
        
        show_message_to_all(f"player {player_list[turn].token} must pay income tax of $200")
        if not player_list[turn].ai:
            oled_big_fill(int(player_list[turn].controller))

            oled_big_text(int(player_list[turn].controller), "Pay income tax of $200", 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(2)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
        player_list[turn].jail = False
        player_list[turn].jail_card = False
        player_list[turn].time_in_jail = 0
        player_list[turn].balance -= 200
        update_info(turn)
    if player_list[turn].position == 38:
        print("Pay luxury tax of $100")
        
        show_message_to_all(f"player {player_list[turn].token} must pay luxury tax of $100")
        if not player_list[turn].ai:
            oled_big_fill(int(player_list[turn].controller))

            oled_big_text(int(player_list[turn].controller), "Pay luxury tax of $100", 0, 0, 1)
            oled_big_show(int(player_list[turn].controller))
            time.sleep(2)
            oled_big_fill(int(player_list[turn].controller))
            oled_big_show(int(player_list[turn].controller))
        player_list[turn].jail = False
        player_list[turn].jail_card = False
        player_list[turn].time_in_jail = 0
        player_list[turn].balance -= 100
        update_info(turn)
    while True:
        # checks to see if teh player is broke after paying the taxes
        
        if player_list[turn].balance >= 0:
            break
        player_list = broke(turn, 1, player_list, False)
    return player_list


# ilorr=if land on railroad
def ilorr():
    def railroad_action(name, player_list):
        list_of_owned_rr = []
        list_of_trains = [train[i].name for i in range(4)]
        # checks to see if a rr is owned
        if train[list_of_trains.index(name)].mortgage == False:
            for z in range(len(player_list)):
                for y in range(len(player_list[z].title_deeds)):
                    list_of_owned_rr.append(player_list[z].title_deeds[y])
            if name in list_of_owned_rr:
                if name not in player_list[turn].title_deeds:
                    print("You must pay for train services")
                    show_message_to_all(f"player {player_list[turn].token} must pay for train services")
                    print("You pay $25 per train station owned")
                    if not player_list[turn].ai:
                        oled_big_fill(int(player_list[turn].controller))

                        oled_big_text(int(player_list[turn].controller), "You must pay for train services. You pay $25 per train station owned", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        time.sleep(2)
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                    player_list[turn].jail = False
                    player_list[turn].jail_card = False
                    player_list[turn].time_in_jail = 0
                    train_owned = 0
                    # adds 1 per railroad owned
                    for i in range(len(player_list)):
                        if "Reading Railroad" in player_list[i].title_deeds:
                            train_owned += 1
                        if "Pennsylvania Railroad" in player_list[i].title_deeds:
                            train_owned += 1
                        if "B. & O. Railroad" in player_list[i].title_deeds:
                            train_owned += 1
                        if "Short Line" in player_list[i].title_deeds:
                            train_owned += 1
                    player_list[turn].balance -= 25 * train_owned
                    update_info(turn)
                    while True:
                        # checks to see if they are broke
                        
                        if player_list[turn].balance > 0:
                            break
                        player_list = broke(turn, 1, player_list, False)
                    for i in range(len(player_list)):
                        if name in player_list[i].title_deeds and i != turn:
                            player_list[i].balance += 25 * train_owned
                            update_info(turn)
                    return player_list
            else:
                # lets player buy a rr
                buyrr = "no"
                if player_list[turn].ai == True:
                    buyrr = AI(player_list, "buyrr", 150, 0, turn)
                if player_list[turn].ai != True:
                    #buyrr = input(f"Do you want to buy {name}(yes or no)?: ")
                    oled_big_text(int(player_list[turn].controller), "Do you want to buy " + name +" $150", 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    oled_text(int(player_list[turn].controller), "<-no       yes->", 0, 36, 1)
                    oled_show(int(player_list[turn].controller))
                    buyrr = "no"
                    while True:
                        if pcf_pin(int(player_list[turn].controller), green) == 0:
                            buyrr = "yes"
                            time.sleep(.3)
                            break
                        if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                            time.sleep(.3)
                            break
                    time.sleep(1)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    oled_fill(int(player_list[turn].controller))
                    oled_show(int(player_list[turn].controller))
                if buyrr == "yes" or (
                    player_list[turn].ai == True
                    and player_list[turn].balance - 150 > 200
                ):
                    if player_list[turn].balance < 150:
                        print("You don't have enough money")
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            oled_big_text(int(player_list[turn].controller), "You don't have enough money", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                    else:
                        print(f"You bought {name} for $150")
                        show_message_to_all(f"player {player_list[turn].token} bought {name}")
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            
                            oled_big_text(int(player_list[turn].controller), "You bought " + name + " for $150", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                        player_list[turn].balance -= 150
                        player_list[turn].title_deeds.append(name)
                        update_info(turn)
                    return player_list
            return player_list
        else:
            if not player_list[turn].ai:
                oled_big_fill(int(player_list[turn].controller))

                oled_big_text(int(player_list[turn].controller), "This RR is mortgaged", 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))

    if player_list[turn].position == 5:
        railroad_action("Reading Railroad", player_list)
    if player_list[turn].position == 15:
        railroad_action("Pennsylvania Railroad", player_list)
    if player_list[turn].position == 25:
        railroad_action("B. & O. Railroad", player_list)
    if player_list[turn].position == 35:
        railroad_action("Short Line", player_list)
    return player_list


# ilou=if land on utility
def ilou(dice):
    def utility_action(name, dice, player_list):
        list_of_owned_u = []
        list_of_utility = [utility[i].name for i in range(2)]
        if utility[list_of_utility.index(name)].mortgage == False:
            for z in range(len(player_list)):
                for y in range(len(player_list[z].title_deeds)):
                    list_of_owned_u.append(player_list[z].title_deeds[y])
            if name in list_of_owned_u:
                if name not in player_list[turn].title_deeds:
                    print("You must pay to utilities")
                    print("You pay $4 per spaces moved")
                    show_message_to_all(f"player {player_list[turn].token} must pay to utilities. They pay $4 per spaces moved")
                    if not player_list[turn].ai:
                        oled_big_fill(int(player_list[turn].controller))

                        
                        oled_big_text(int(player_list[turn].controller), "You must pay to utilities. You pay $4 per spaces moved", 0, 0, 1)
                        oled_big_show(int(player_list[turn].controller))
                        time.sleep(2)
                        oled_big_fill(int(player_list[turn].controller))
                        oled_big_show(int(player_list[turn].controller))
                    player_list[turn].balance -= 4 * dice
                    update_info(turn)
                    while True:
                        
                        if player_list[turn].balance > 0:
                            break
                        player_list = broke(turn, 1, player_list, False)
                    for i in range(len(player_list)):
                        if name in player_list[i].title_deeds and i != turn:
                            player_list[i].balance += 4 * dice
                            update_info(turn)
                    return player_list
            else:
                buyu = "no"
                if player_list[turn].ai == True:
                    buyu = AI(player_list, "buyu", 150, 0, turn)
                if player_list[turn].ai != True:
                    #buyu = input(f"Do you want to buy {name}(yes or no)?: ")
                    oled_big_text(int(player_list[turn].controller), "Do you want to buy " + name, 0, 0, 1)
                    oled_big_show(int(player_list[turn].controller))
                    oled_text(int(player_list[turn].controller), "<-no       yes->", 0, 36, 1)
                    oled_show(int(player_list[turn].controller))
                    buyu = "no"
                    while True:
                        if pcf_pin(int(player_list[turn].controller), green) == 0:
                            buyu = "yes"
                            time.sleep(.3)
                            break
                        if pcf_pin(int(player_list[turn].controller), yellow) == 0:
                            time.sleep(.3)
                            break
                    time.sleep(1)
                    oled_big_fill(int(player_list[turn].controller))
                    oled_big_show(int(player_list[turn].controller))
                    oled_fill(int(player_list[turn].controller))
                    oled_show(int(player_list[turn].controller))
                if buyu == "yes" or (
                    player_list[turn].ai == True
                    and player_list[turn].balance - 150 > 200
                ):
                    if player_list[turn].balance < 150:
                        print("You don't have enough money")
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            oled_big_text(int(player_list[turn].controller), "You don't have enough money", 0, 0, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                    else:
                        print(f"You bought {name} for $150")
                        show_message_to_all(f"player {player_list[turn].token} bought {name}")
                        if not player_list[turn].ai:
                            oled_big_fill(int(player_list[turn].controller))

                            
                            oled_big_text(int(player_list[turn].controller), "You bought", 0, 0, 1)
                            oled_big_text(int(player_list[turn].controller), name, 0, 15, 1)
                            oled_big_text(int(player_list[turn].controller), "for $150", 0, 25, 1)
                            oled_big_show(int(player_list[turn].controller))
                            time.sleep(2)
                            oled_big_fill(int(player_list[turn].controller))
                            oled_big_show(int(player_list[turn].controller))
                        player_list[turn].balance -= 150
                        update_info(turn)
                    return player_list
            return player_list
        else:
            print("This utility has been mortgaged")
            if not player_list[turn].ai:
                oled_big_fill(int(player_list[turn].controller))

                oled_big_text(int(player_list[turn].controller), "This utility is mortgaged", 0, 0, 1)
                oled_big_show(int(player_list[turn].controller))
                time.sleep(2)
                oled_big_fill(int(player_list[turn].controller))
                oled_big_show(int(player_list[turn].controller))

    if player_list[turn].position == 12:
        utility_action("Electric Company", dice, player_list)
    if player_list[turn].position == 28:
        utility_action("Water Works", dice, player_list)
    return player_list


board = make_bts_board()
num_turn = 0

for i in range(len(player_list)):
    update_info(i)
while True:
    # runs the game
    depth = int(30 / len(player_list))
    title_deed, player_list = check_color_set(turn)
    player_list, turn, dice, dice1, dice2 = moves(turn_thing)
    turn_thing += 1
    # lands on chance or chest
    if player_list[turn].position in [2, 7, 17, 22, 33, 36]:
        player_list = ilocc()
    # lands on property
    if player_list[turn].position in [1, 3, 6, 8, 9, 11, 13, 14, 16, 18, 19, 21, 23, 24, 26, 27, 29, 31, 32, 34, 37, 39]:
        player_list = ilotd()
    # lands on special place
    if player_list[turn].position in [0, 10, 20, 30, 4, 38]:
        player_list = ilosp(player_list)
    # lands on railroad
    if player_list[turn].position in [5, 15, 25, 35]:
        player_list = ilorr()
    # land on utility
    if player_list[turn].position in [12, 28]:
        player_list = ilou(dice)
    if player_list[turn].balance < 0:
        player_list = broke(turn, 1, player_list, True)
    num_turn += 1
    time.sleep(1)
