from machine import Pin, PWM
#from robopong import main
import asyncio
#from drv8825 import DRV8825
import network

program_pin = Pin(19, Pin.IN, Pin.PULL_UP)
if not program_pin.value():
    print("Stop program")
else:
    print("Continue program")
    #th = _thread.start_new_thread(main_loop, tuple())
    #asyncio.run(main())

    #stepper = DRV8825(step_pin=5)

    #stepper.steps(1000)
    #pin = Pin(18, Pin.OUT)
    #pwm = PWM(pin, freq=50)

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="robopong", key="topspin")
    