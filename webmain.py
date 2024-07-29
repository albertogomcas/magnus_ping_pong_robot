from microdot import Microdot, redirect, Response, send_file
from machine import Pin
import asyncio

pin = Pin(12, Pin.OUT)
pin.off()

async def blink(n, up=1, down=1):
    for i in range(0, n):
        pin.on()
        await asyncio.sleep(up)
        pin.off()
        await asyncio.sleep(down)


Response.default_content_type = 'text/html'

esp_app = Microdot()

@esp_app.get("/")
async def index(request):
    return send_file("static/index.html")

@esp_app.route('/static/<path:path>')
async def static(request, path):
    if ".." in path:
        return "Not found", 404
    return send_file("static/"+path)

@esp_app.route("/cmd/<command>")
async def cmd(request, command):
    actions = {
        "on": pin.on,
        "off": pin.off,
        "blink": blink,

    }
    print(command)
    try:
        cmd, *args = command.split(",")
        print(cmd, args)
        if args:
            await actions[cmd](*[float(a) for a in args])
        else:
            actions[cmd]()
    except KeyError:
        return "Not found", 404
    except Exception as e:
        return f"Exception {cmd} {e}", 404

    return "Success", 200


if __name__ == "__main__":
    try:
        esp_app.run(port=80, debug=True)
    except:
        esp_app.shutdown()