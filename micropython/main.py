import machine
import os
import pbm
import random
import ssd1306
import time


def slideshow(oled, imageDir='pbms', interval=1):
    images = os.listdir(imageDir)

    while True:
        imgName = random.choice(images)
        fb, h, w = pbm.read_pbm_p4(f"pbms/{imgName}")
        oled.blit(fb, 0, 0)
        oled.show()
        time.sleep(interval)

i2c = machine.I2C(1, sda=machine.Pin(14), scl=machine.Pin(15))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
slideshow(oled)
