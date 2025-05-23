import machine
class DevFlags:
    simulation_mode = False
    run_app = True

def update(branch="master"):
    import senko
    OTA = senko.Senko(
        user="albertogomcas",
        repo="magnus_ping_pong_robot",
        working_dir="",
        branch=branch,
        files=["main.py", "dev.py", "parts.py", "servo.py", "stservo_wrapper.py", "ujrpc.py", "microdot.mpy",
               "webmain.py"],
    )
    if OTA.update():
        print("Updated to latest version, rebooting...")
        machine.reset()
