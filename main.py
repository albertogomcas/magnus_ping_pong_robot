from machine import Pin
from robopong import main
import asyncio


program_pin = Pin(19, Pin.IN, Pin.PULL_UP)
if not program_pin.value():
    print("Stop program")
else:
    print("Continue program")
    #th = _thread.start_new_thread(main_loop, tuple())
    asyncio.run(main())
