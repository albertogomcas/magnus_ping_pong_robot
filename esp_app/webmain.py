from microdot import Microdot, Response
import machine

import dev
from magnus import UsedPins, Magnus
from ujrpc import JRPCService
import asyncio

UsedPins.sanity_check()
magnus = Magnus()

async def main():
    magnus.halt()

    feed_task = asyncio.create_task(magnus.feeder.run())
    shaker_task = asyncio.create_task(magnus.shaker.run())

    offline = False
    calibrated = False

    try:
        previous_active = None
        wait = 0

        while True:
            await asyncio.sleep(0.1)
            active = False

            if not offline and not calibrated:
                value = magnus.supply.esc_alive()
                wait += 1

                if value:
                    magnus.calibrate()
                    magnus.feeder_servo.set_wheel_mode_closed_loop()
                    calibrated = True
                    wait = 0

            if active != previous_active:
                if active:
                    previous_active = True
                    magnus.launcher.configure(speed=8, topspin=0, sidespin=0)
                    magnus.launcher.activate()
                    magnus.feeder.activate()

                else:
                    previous_active = False
                    magnus.launcher.halt()
                    magnus.feeder.halt()

            if not magnus.supply.esc_alive():
                calibrated = False
                continue

    except Exception as e:
        magnus.halt()
        feed_task.cancel()
        shaker_task.cancel()
        raise

jrpc = JRPCService(api_version=1)
jrpc.debug = True
Response.default_content_type = 'text/html'
esp_app = Microdot()

@esp_app.get("/")
async def index(request):
    return "Magnus ESP32 is ready"

@esp_app.route('/rpc', methods=["POST"])
async def rpc(request):
    return jrpc.handle_rpc(request.json)

@jrpc.fn(name="status")
def status(r):
    status = magnus.status()
    return status

@jrpc.fn(name="feed_one")
def feed_one(r):
    magnus.feed_one()
    return status(r)

@jrpc.fn(name="calibrate_aim_zero")
def calibrate_aim_zero(r):
    try:
        return magnus.aimer.calibrate()
    except:
        return False

@jrpc.fn(name="sync_settings")
def sync_settings(r, settings):
    print(f"Got settings {settings}")
    magnus.set_settings(**settings)
    return status(r)

@jrpc.fn(name="reset")
def reset(r):
    machine.reset()

@jrpc.fn(name="interrupt")
def interrupt(r):
    print(f"interrupting server")
    esp_app.shutdown()

@jrpc.fn(name="enable_simulation")
def enable_simulation(r):
    dev.DevFlags.simulation_mode = True

@jrpc.fn(name="disable_simulation")
def disable_simulation(r):
    dev.DevFlags.simulation_mode = False