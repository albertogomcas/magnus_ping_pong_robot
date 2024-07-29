from machine import Pin
#from robopong import main
#from drv8825 import DRV8825
import network
from secrets import Wifi
from webmain import esp_app

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



nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect(Wifi.ssid, Wifi.password)
nic.ifconfig(('10.0.0.47', '255.255.255.0', '10.0.0.138', '8.8.8.8'))
print(nic.isconnected())
print(nic.ifconfig())




try:
    esp_app.run(port=80, debug=True)
except:
    esp_app.shutdown()
    raise