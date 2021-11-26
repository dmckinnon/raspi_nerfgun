from guizero import App, PushButton, Slider, Text
import RPi.GPIO as gpio
import alsaaudio as audio
from subprocess import call
import board
import neopixel
from time import sleep
import threading
import os
#from ButtonHandlerClass import ButtonHandler


#################################
# Config vars
FIRING_SPEED = 0 # 0 - 100
SFX_VOLUME = 0 # 0 - 255
CANNON_LED_BRIGHTNESS = 0 # 0 - 255
AMMO_COUNT = 0 # 0 - however many fits
SUIT_LED_BRIGHTNESS = 0 # 0 - 255
BATTERY_LEVEL = 0 # 0 - 100%; read from IO, not config

def ReadConfig():
    cfg = open('power_armour.cfg')
    for line in cfg:
        vals = line.split()
        if 'FIRING_SPEED' in vals[0]:
            FIRING_SPEED = int(vals[1])
        elif 'SFX_VOLUME' in vals[0]:
            SFX_VOLUME = int(vals[1])
        elif 'CANNON_LED_BRIGHTNESS' in vals[0]:
            CANNON_LED_BRIGHTNESS = int(vals[1])
        elif 'AMMO_COUNT' in vals[0]:
            AMMO_COUNT = int(vals[1])
        elif 'SUIT_LED_BRIGHTNESS' in vals[0]:
            SUIT_LED_BRIGHTNESS = int(vals[1])

################################
# Globals for event handlers and main
cannonLightsActive = True
suitLightsActive = True
gunleds = neopixel.NeoPixel(board.D21, 1)
motorDriverPWM = None

# GPIO pin 3 works. Why didn't 2?
FIRE_BUTTON = 3
HALL_EFFECT = 4
MOTOR_DRIVER = 16
MOTOR_DRIVER_2 = 6


################################
# Event handlers for GUI buttons
def CannonLightsToggle():
    global cannonLightsActive
    cannonLightsActive = not cannonLightsActive

    # debug
    SetCannonLightsDefault()

def SuitLightsToggle():
    global suitLightsActive
    suitLightsActive = not suitLightsActive

def SetCannonLightsBrightness(slider_value):
    global CANNON_LED_BRIGHTNESS
    CANNON_LED_BRIGHTNESS = int(slider_value)

def SetSuitLightsBrightness(slider_value):
    global SUIT_LED_BRIGHTNESS
    SUIT_LED_BRIGHTNESS = int(slider_value)

def SetGunPower(slider_value):
    global FIRING_SPEED
    FIRING_SPEED = slider_value

def SetVolume(slider_value):
    global SFX_VOLUME
    # set this for write-out for next time
    SFX_VOLUME = slider_value

    mixer = audio.Mixer('Headphone', cardindex=1)
    mixer.setvolume(slider_value)

def AddAmmo():
    global AMMO_COUNT
    AMMO_COUNT += 1

    # debug
    FireGun()

def MaybeSleepScreen(sleepScreen):
    # This is called when the Hall Effect sensor triggers
    # This means that the magnet of the screen cover has moved
    # So sleep the display if covered or otherwise wake
    if sleepScreen:
        os.system('gpio -g pwm 18 0')
    else:
        os.system('gpio -g pwm 18 256')

def Shutdown():
    # Save system config out to a file

    gpio.cleanup()

    # shutdown the system
    call("sudo shutdown --poweroff", shell=True)

################################
# GPIO Control
def SetupPins():
    global FIRE_BUTTON
    global HALL_EFFECT
    global MOTOR_DRIVER
    global MOTOR_DRIVER_2
    global motorDriverPWM

    os.system('gpio -g mode 18 PWM')
    
    gpio.setup(FIRE_BUTTON, gpio.IN, pull_up_down=gpio.PUD_DOWN)
    gpio.setup(HALL_EFFECT, gpio.IN)

    # PWM pins
    gpio.setup(MOTOR_DRIVER, gpio.OUT)
    motorDriverPWM = gpio.PWM(MOTOR_DRIVER, 2000) # update at 2kHz

    # RX pin for arduino comms    

    # initial output values

def SetCannonLightsDefault():
    global CANNON_LED_BRIGHTNESS
    # somerthing something WS28181 pins
    # ba basic yellow glow at 1/2 max brightness
    b = CANNON_LED_BRIGHTNESS/2
    r = b
    g = 0.5*b
    gunleds[0] = (r, g, 0)
    print("led 0 at brightness " + str(r) + " " + str(g))

def SetSuitLightsDefault():
    global SUIT_LED_BRIGHTNESS
    # somerthing something WS28181 pins
    # ba basic yellow glow at 1/2 max brightness
    b = CANNON_LED_BRIGHTNESS/2
    gunleds[0] = (0, b, b)

def FireGun():
    global SUIT_LED_BRIGHTNESS
    global motorDriverPWM
    global FIRING_SPEED
    gunleds[0] = (0, 0, SUIT_LED_BRIGHTNESS)
    print("firing")
    # sfx
    # vfx

    # Debug for motor driving
    motorDriverPWM.start(int(FIRING_SPEED))
    sleep(2)
    motorDriverPWM.stop()

def GPIOLoop():
    global FIRE_BUTTON
    global HALL_EFFECT
    lastPinVals = {}
    lastPinVals[FIRE_BUTTON] = gpio.input(FIRE_BUTTON)
    lastPinVals[HALL_EFFECT] = gpio.input(HALL_EFFECT)
    
    while(True):
        # check each input in turn

        # Firing button
        currPinVal = gpio.input(FIRE_BUTTON)
        if currPinVal == gpio.HIGH and lastPinVals[FIRE_BUTTON] == gpio.LOW:
            FireGun()
            # debounce
            sleep(0.1)
        # reset previous value
        lastPinVals[str(FIRE_BUTTON)] = currPinVal


        # Hall effect sensor for display cover
        currPinVal = gpio.input(HALL_EFFECT)
        if currPinVal == gpio.LOW and lastPinVals[HALL_EFFECT] == gpio.HIGH:
            MaybeSleepScreen(True)
            sleep(0.1)
        elif currPinVal == gpio.HIGH and lastPinVals[HALL_EFFECT] == gpio.LOW:
            MaybeSleepScreen(False)
            sleep(0.1)
        lastPinVals[HALL_EFFECT] = currPinVal

        # Debounce gpio loop
        sleep(0.01)
        

################################
# Main control
if __name__=="__main__":
    # read global vars from file.
    # If unable to read, assume system defaults
    ReadConfig()

    # set up GPIO
    SetupPins()

    # Set initial volume
    SetVolume(SFX_VOLUME)

    # start lights
    if cannonLightsActive:
        SetCannonLightsDefault()

    if suitLightsActive:
        SetSuitLightsDefault()

    # Construct GUI
    app = App()#layout="grid")

    # Create buttons
    cannonLightsControl = PushButton(app, command=CannonLightsToggle, text="Gun lights")
    suitLightsControl = PushButton(app, command=SuitLightsToggle, text="Suit lights")
    addAmmoControl = PushButton(app, command=AddAmmo, text="Add shot")

    # Sliders for lights and power
    cannonLightsTitle = Text(app, text="Gun lights")
    cannonLightsBrightness = Slider(app, command=SetCannonLightsBrightness, start=0, end=255)
    suitLightsTitle = Text(app, text="Suit lights")
    suitLightsBrightness = Slider(app, command=SetSuitLightsBrightness, start=0, end=255)
    volumeControlTitle = Text(app, text="Volume")
    sfxVolume = Slider(app, command=SetVolume, start=0, end=100)
    firingSpeedTitle = Text(app, text="Power")
    firingSpeedControl = Slider(app, command=SetGunPower, start=0, end=100)

    # Power
    shutdownButton = PushButton(app, command=Shutdown, text="Shutdown")

    # Before blocking this thread on the GUI loop, start the GPIO loop
    gpioThread = threading.Thread(target=GPIOLoop)
    gpioThread.start()

    app.display()
    # This is a blocking loop. The GPIO thread should be kicked off before this
    # or everything should be event based
        
    
    
