from machine import Pin
from webmain import esp_app, main
import asyncio
from dev import DevFlags

def run():
    asyncio.create_task(main())
    esp_app.run(port=80, debug=True)

program_pin = Pin(19, Pin.IN, Pin.PULL_UP)

if (not program_pin.value()) or (not DevFlags.run_app):
    print("Stop program")
else:
    print("Continue program")
    try:
        run()
    except:
        esp_app.shutdown()
        raise

print("Start webrepl")
import webrepl
webrepl.start()




