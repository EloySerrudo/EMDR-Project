from os import uname
from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms

NUMLED = 60 # Number of LEDs. Actually 61, but the last one is not used
ID = 'EMDR Lightbar'

machine = uname().machine
pin_no = 0
if 'Teensy 4.0' in machine:
    pin_no = 'D1'
elif 'ESP module' in machine:
    pin_no = 5
elif 'Raspberry Pi Pico'  in machine:
    pin_no = 16
elif 'ESP32 module' in machine:
    pin_no = 13
else:
    raise Exception('Unsupported platform')

pin = Pin(pin_no, Pin.OUT)
np = NeoPixel(pin, NUMLED, bpp=3)

def clear():
    np.fill([0] * len(np))

def test():
    global np
    clear()
    np[0] = (0, 0x20, 0)
    np[-1] = (0x20, 0, 0)
    np.write()
    sleep_ms(500)
    clear()
    np.write()


def loop():
    global np
    col = (0x0f, 0, 0)
    while True:
        line = input()
        cmd, val, *_ = (line + ' ').split(' ')
        try:
            val = int(val)
        except:
            val = 0
        try:
            if cmd == 'c':
                # color cmd
                col = ((val >> 16) & 0xff, (val >> 8) & 0xff, val & 0xff)
            elif cmd == 'l':
                # led cmd
                clear()
                np[val - 1] = col
                np.write()
            elif cmd == 't':
                # test command
                clear()
                np[0] = col
                np[-1] = col
                np.write()
            elif cmd == 'i':
                # id command
                print(ID)
        except:
            print('error')

test()
loop()         