from microdot import Microdot, Response
import machine
import network
import time

import dev
from magnus import UsedPins, Magnus
from ujrpc import JRPCService
import asyncio
from secrets import Wifi
from wifi_probe import connect_strongest

UsedPins.sanity_check()
import gc
gc.collect()
print(f"Free memory before Magnus: {gc.mem_free()}")

# 1. Instantiate Magnus first - before WiFi takes memory
magnus = Magnus()

# 2. Now connect WiFi so ESPNow knows the channel
print("[Webmain] Connecting WiFi...")
nic = network.WLAN(network.STA_IF)
nic.active(True)
if not nic.isconnected():
    nic.ifconfig(('10.0.0.47', '255.255.255.0', '10.0.0.138', '8.8.8.8'))
    connect_strongest(nic, Wifi)
print(f"[Webmain] WiFi connected, channel={nic.config('channel')}")

# 3. Initialize ESP-NOW remote now that WiFi channel is known
magnus.enable_remote()

async def main():
    magnus.halt()

    feed_task = asyncio.create_task(magnus.feeder.run())
    shaker_task = asyncio.create_task(magnus.shaker.run())
    remote_task = asyncio.create_task(magnus.remote.run()) if magnus.remote else None

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
                    if not dev.DevFlags.simulation_mode:
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
        if remote_task:
            remote_task.cancel()
        raise

jrpc = JRPCService(api_version=1)
jrpc.debug = dev.DevFlags.debug
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
    #print(f"Got settings {settings}")
    magnus.set_settings(**settings)
    return status(r)

# --- Aim ---

@jrpc.fn(name="set_aim")
def set_aim(r, tilt=None, pan=None):
    """Set absolute aim position. Omit either axis to keep it unchanged."""
    aim_st = magnus.aimer.status()
    magnus.aimer.aim(
        vangle=tilt if tilt is not None else aim_st["tilt"],
        hangle=pan if pan is not None else aim_st["pan"],
    )
    return status(r)

@jrpc.fn(name="aim_up")
def aim_up(r, step=1):
    magnus.aimer.up(step=step)
    return status(r)

@jrpc.fn(name="aim_down")
def aim_down(r, step=1):
    magnus.aimer.down(step=step)
    return status(r)

@jrpc.fn(name="aim_left")
def aim_left(r, step=1):
    magnus.aimer.left(step=step)
    return status(r)

@jrpc.fn(name="aim_right")
def aim_right(r, step=1):
    magnus.aimer.right(step=step)
    return status(r)

@jrpc.fn(name="aim_center")
def aim_center(r):
    magnus.aimer.middle()
    return status(r)

# --- Launcher ---

@jrpc.fn(name="set_launcher")
def set_launcher(r, speed=None, spin_angle=None, spin_strength=None, active=None):
    """Set launcher parameters individually. Omit any param to keep it unchanged."""
    import math as _math
    st = magnus.launcher.status()
    spd = speed if speed is not None else st["speed"]
    angle = spin_angle if spin_angle is not None else st["spin_angle"]
    strength = spin_strength if spin_strength is not None else st["spin_strength"]
    was_active = st["active"] if active is None else active

    topspin = _math.cos(_math.radians(angle)) * strength / 100
    sidespin = _math.sin(_math.radians(angle)) * strength / 100
    magnus.launcher.configure(speed=spd, topspin=topspin, sidespin=sidespin)

    if was_active:
        magnus.launcher.activate()
    else:
        magnus.launcher.halt()
    return status(r)

@jrpc.fn(name="activate")
def activate(r):
    """Activate launcher (and feeder if interval is set)."""
    magnus.launcher.activate()
    magnus.feeder.activate()
    return status(r)

@jrpc.fn(name="halt")
def halt(r):
    """Stop launcher and feeder."""
    magnus.launcher.halt()
    return status(r)

@jrpc.fn(name="speed_up")
def speed_up(r, step=2):
    magnus.launcher.speed_up(step=step)
    return status(r)

@jrpc.fn(name="speed_down")
def speed_down(r, step=2):
    magnus.launcher.speed_down(step=step)
    return status(r)

@jrpc.fn(name="increase_spin")
def increase_spin(r, step=10):
    magnus.launcher.increase_spin(step=step)
    return status(r)

@jrpc.fn(name="decrease_spin")
def decrease_spin(r, step=10):
    magnus.launcher.decrease_spin(step=step)
    return status(r)

@jrpc.fn(name="no_spin")
def no_spin(r):
    magnus.launcher.no_spin()
    return status(r)

@jrpc.fn(name="spin_T")
def spin_T(r, strength=0.5):
    magnus.launcher.spin_T(strength=strength)
    return status(r)

@jrpc.fn(name="spin_B")
def spin_B(r, strength=0.5):
    magnus.launcher.spin_B(strength=strength)
    return status(r)

@jrpc.fn(name="spin_L")
def spin_L(r, strength=0.5):
    magnus.launcher.spin_L(strength=strength)
    return status(r)

@jrpc.fn(name="spin_R")
def spin_R(r, strength=0.5):
    magnus.launcher.spin_R(strength=strength)
    return status(r)

@jrpc.fn(name="spin_TL")
def spin_TL(r, strength=0.5):
    magnus.launcher.spin_TL(strength=strength)
    return status(r)

@jrpc.fn(name="spin_TR")
def spin_TR(r, strength=0.5):
    magnus.launcher.spin_TR(strength=strength)
    return status(r)

@jrpc.fn(name="spin_BL")
def spin_BL(r, strength=0.5):
    magnus.launcher.spin_BL(strength=strength)
    return status(r)

@jrpc.fn(name="spin_BR")
def spin_BR(r, strength=0.5):
    magnus.launcher.spin_BR(strength=strength)
    return status(r)

@jrpc.fn(name="spin_random")
def spin_random(r):
    magnus.launcher.spin_random()
    return status(r)

# --- Feed interval ---

@jrpc.fn(name="set_feed_interval")
def set_feed_interval(r, interval):
    """Set ball feed interval in seconds."""
    magnus.feeder.set_ball_interval(interval)
    return status(r)

@jrpc.fn(name="interval_up")
def interval_up(r, step=0.25):
    magnus.interval_up(step=step)
    return status(r)

@jrpc.fn(name="interval_down")
def interval_down(r, step=0.25):
    magnus.interval_down(step=step)
    return status(r)

@jrpc.fn(name="set_sequence")
def set_sequence(r, sequence):
    #print(f"Got sequence {sequence}")
    magnus.set_sequence(sequence)
    return status(r)

@jrpc.fn(name="start_sequence")
def start_sequence(r, settings):
    #print(f"Got start sequence settings {settings}")
    magnus.start_sequence(**settings)
    return status(r)

@jrpc.fn(name="stop_sequence")
def stop_sequence(r):
    magnus.stop_sequence()
    return status(r)

@jrpc.fn(name="list_presets")
def list_presets(r):
    return magnus.drill_store.list_presets()

@jrpc.fn(name="save_preset")
def save_preset(r, slot, name, preset):
    return magnus.drill_store.save_preset(slot, name, preset)

@jrpc.fn(name="delete_preset")
def delete_preset(r, slot):
    return magnus.drill_store.delete_preset(slot)

@jrpc.fn(name="apply_preset")
def apply_preset(r, slot):
    return magnus.apply_preset(slot)

@jrpc.fn(name="list_sequences")
def list_sequences(r):
    return magnus.drill_store.list_sequences()

@jrpc.fn(name="save_sequence")
def save_sequence(r, slot, name, preset_slots):
    return magnus.drill_store.save_sequence(slot, name, preset_slots)

@jrpc.fn(name="delete_sequence")
def delete_sequence(r, slot):
    return magnus.drill_store.delete_sequence(slot)

@jrpc.fn(name="start_saved_sequence")
def start_saved_sequence(r, slot, randomize_order=False, loop=True, feed_interval=None):
    magnus.start_saved_sequence(
        slot,
        randomize_order=randomize_order,
        loop=loop,
        feed_interval=feed_interval,
    )
    return status(r)

@jrpc.fn(name="reset")
def reset(r):
    machine.reset()

@jrpc.fn(name="interrupt")
def interrupt(r):
    print(f"[Webmain] interrupting server")
    esp_app.shutdown()

@jrpc.fn(name="enable_simulation")
def enable_simulation(r):
    dev.DevFlags.simulation_mode = True

@jrpc.fn(name="disable_simulation")
def disable_simulation(r):
    dev.DevFlags.simulation_mode = False