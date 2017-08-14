# noinspection PyUnresolvedReferences
import RPi.GPIO as GPIO
import time

# setup pin 11, 12, 13 & 15 as outputs
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)

BLINK = 0.05

while True:
    GPIO.output(11, GPIO.HIGH)
    time.sleep(BLINK)
    GPIO.output(11, GPIO.LOW)
    GPIO.output(12, GPIO.HIGH)
    time.sleep(BLINK)
    GPIO.output(12, GPIO.LOW)
    GPIO.output(13, GPIO.HIGH)
    time.sleep(BLINK)
    GPIO.output(13, GPIO.LOW)
    GPIO.output(15, GPIO.HIGH)
    time.sleep(BLINK)
    GPIO.output(15, GPIO.LOW)
