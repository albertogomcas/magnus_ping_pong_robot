---
name: flash-robopong
description: Upload selected RoboPong MicroPython application files to the robot controller or ESP32-C6 remote, verify transfers, and restart. Use when asked to flash or update either device.
---

# Flash RoboPong

Only flash when the user requests it. Confirm the launcher and feeder are stopped before interrupting the controller; never test movement or starting a drill automatically. If their state is unknown, ask the user.

Select the changed application files needed for the requested update, including dependencies, from the current workspace. Explicitly identify each target and serial port; recent ports were robot COM4 and remote COM3, but confirm if uncertain. For changes to the protocol, update both devices. Do not copy secrets, boot settings, device data, or unrelated files.

Run the helper from the repository root, passing only the required basenames:

```powershell
python .github\skills\flash-robopong\flash.py robot --port COM4 --files magnus.py parts.py
python .github\skills\flash-robopong\flash.py remote --port COM3 --files main.py oled_display.py
```

For both devices, update the robot first. The helper checks the board type, uploads selected files, compares SHA-256 hashes, resets, and passively checks serial output. It does not erase firmware, print credentials, or change configuration. `wifi_probe.py` on the remote is sourced from `esp_app\wifi_probe.py`.

Read the concise result, act on errors, and report which devices were updated and whether startup was observed. If a copy or hash check fails, the device may contain a partial update; do not claim success or blindly reset it. If startup cannot be observed, distinguish verified files from unverified runtime behavior. Do not install dependencies unless the helper reports them missing. Never inspect or print `secrets.py`.
