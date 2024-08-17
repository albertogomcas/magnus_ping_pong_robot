from microdot import Microdot, Response
from machine import Pin, UART
import asyncio
from ujrpc import JRPCService
import time

jrpc = JRPCService(api_version=1)
jrpc.debug = True

pin = Pin(12, Pin.OUT)
pin.off()

uart = UART(2, baudrate=115200, tx=Pin(25), rx=Pin(26))

@jrpc.fn(name="led_on")
def led_on(r):
     pin.on()
     return "led is on"

@jrpc.fn(name="led_off")
def led_off(r):
     pin.off()
     return "led is off"

@jrpc.fn(name="blink")
def blink(r, n, up=1, down=1):
    for i in range(0, n):
        pin.on()
        #await asyncio.sleep(up)
        time.sleep_ms(int(up*1000))
        pin.off()
        #await asyncio.sleep(down)
        time.sleep_ms(int(down*1000))

    return "blinked"

@jrpc.fn(name="arduino")
def arduino(r, raw):
    uart.write(b"\r\n\r\n")
    time.sleep(2)
    uart.flush()
    uart.write(raw.encode("ascii")+f"\n")
    time.sleep(1)
    ret = uart.readline()
    return ret

Response.default_content_type = 'text/html'

esp_app = Microdot()

@esp_app.get("/")
async def index(request):
    return "robopong"

@esp_app.route('/rpc', methods=["POST"])
async def rpc(request):
    return jrpc.handle_rpc(request.json)
