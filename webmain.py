from microdot import Microdot, redirect, Response, send_file

Response.default_content_type = 'text/html'

esp_app = Microdot()

@esp_app.get("/")
async def index(request):
    return send_file("index.html")

@esp_app.route('/<path:path>')
async def static(request, path):
    if ".." in path:
        return "Not found", 404
    #with open(path, "rb") as f:
        #return f.read()
    return send_file(path)


if __name__ == "__main__":
    try:
        esp_app.run(port=80, debug=True)
    except:
        esp_app.shutdown()