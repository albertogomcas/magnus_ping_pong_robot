from microdot import Microdot, redirect, Response, send_file
from machine import Pin

pin = Pin(12, Pin.OUT)
pin.off()

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
def cmd(request, command):
    actions = {
        "on": pin.on,
        "off": pin.off,

    }
    try:
        actions[command]()
        return redirect("/")
    except:
        return "Invalid command", 400




if __name__ == "__main__":
    try:
        esp_app.run(port=80, debug=True)
    except:
        esp_app.shutdown()