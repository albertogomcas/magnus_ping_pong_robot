# ESP-NOW Remote Setup Guide

This guide walks through setting up the ESP-NOW remote control system for RoboPong.

## Overview

The system consists of two ESP32 devices:
1. **Main Controller** - The existing RoboPong ESP32 that controls the hardware
2. **Remote Device** - New battery-powered ESP32 with keypad and OLED display

## Hardware Requirements

### Remote Device
- ESP32 development board
- 3x4 matrix keypad
- 128x64 I2C OLED display (SSD1306)
- Battery pack (2S LiPo or 3x AA batteries with voltage regulator)
- Resistors for voltage divider (optional, for battery monitoring)
- Enclosure

### Wiring Diagram (Remote Device)

```
Keypad Matrix:
  Row 1 → GPIO 15
  Row 2 → GPIO 2  
  Row 3 → GPIO 0
  Col 1 → GPIO 4
  Col 2 → GPIO 16
  Col 3 → GPIO 17
  Col 4 → GPIO 5

OLED Display (I2C):
  SDA → GPIO 21
  SCL → GPIO 22
  VCC → 3.3V
  GND → GND

Battery Monitoring (optional):
  Battery+ → Voltage Divider → GPIO 35
  (Use 10kΩ + 10kΩ resistors for 2:1 division)
```

## Software Setup

### Step 1: Get MAC Addresses

1. **On Main Controller ESP32:**
   ```python
   # Run get_mac.py or in REPL:
   import network
   sta = network.WLAN(network.STA_IF)
   sta.active(True)
   print(':'.join(['%02x' % b for b in sta.config('mac')]))
   ```
   
2. **On Remote Device ESP32:**
   Do the same to verify its MAC address

3. **Save these MAC addresses** - you'll need them for configuration

### Step 2: Install Required Libraries

Both devices need MicroPython firmware. The remote device additionally needs:

```bash
# Install ssd1306 OLED driver
# Download from: https://github.com/micropython/micropython/blob/master/drivers/display/ssd1306.py
# Upload to remote ESP32 as ssd1306.py
```

### Step 3: Configure MAC Addresses

1. **In remote_device/main.py:**
   ```python
   # Replace this line with your main controller's MAC address
   RECEIVER_MAC = b'\xff\xff\xff\xff\xff\xff'  # Change this!
   ```
   
   Example:
   ```python
   RECEIVER_MAC = b'\x24\x6f\x28\xa1\xb2\xc3'
   ```

2. **Optionally in esp_app/magnus.py:**
   If you want to filter messages from specific sender:
   ```python
   self.remote = ESPNowRemote(sender_mac=b'\xaa\xbb\xcc\xdd\xee\xff')
   ```

### Step 4: Upload Firmware

**Main Controller:**
- Update existing files:
  - `esp_app/parts.py` (already modified with ESPNowRemote class)
  - `esp_app/magnus.py` (already modified to use ESPNowRemote)
  - `esp_app/webmain.py` (no changes needed)

**Remote Device:**
- Upload all files from `esp_app/remote_device/`:
  - `main.py`
  - `keypad.py`
  - `oled_display.py`
  - `espnow_sender.py`
  - `ssd1306.py` (external library)

### Step 5: Test the System

1. **Power on Main Controller** - Wait for it to boot and calibrate
2. **Power on Remote Device** - You should see the OLED display show Layer 0
3. **Press keys** - Watch the serial console for debug messages
4. **Test all layers** - Press * to cycle through layers

## Usage

### Key Layers

**Layer 0 - CONTROL** (Press * to switch)
```
     2↑        Layer indicator: L0:CONTROL
  4← 5⊙ 6→     2 = Aim Up
     8↓        4 = Aim Left, 5 = Center, 6 = Aim Right
  *    0  #    8 = Aim Down
               0 = Feed One Ball
               # = Start/Stop
               * = Switch Layer
```

**Layer 1 - SPIN** (Press * to switch)
```
  1↖  2   3↗   Layer indicator: L1:SPIN
  4   5   6    1-9 = Spin direction presets
  7↙  8   9↘   1=TopLeft, 2=Top, 3=TopRight
  *   0   #    4=Left, 5=Random, 6=Right
               7=BottomLeft, 8=Bottom, 9=BottomRight
               0 = No Spin
```

**Layer 2 - SETTINGS** (Press * to switch)
```
  1    3       Layer indicator: L2:SETTINGS
  4    6       1 = Speed Up, 3 = Speed Down
  7    9       4 = Decrease Spin, 6 = Increase Spin
  *   0   #    7 = Interval Up, 9 = Interval Down
```

### Battery Management

- Battery voltage is displayed in top-right corner
- Low battery warning (!) appears when voltage < 3.3V
- Remote enters deep sleep after 60 seconds of inactivity
- Press any key to wake from sleep

## Troubleshooting

### Remote doesn't connect
- Verify MAC addresses are correct
- Check both devices have WiFi enabled (station mode)
- Ensure devices are within range (~100m outdoors, less indoors)

### Keys not responding
- Check keypad wiring
- Verify GPIO pin assignments match your keypad
- Watch serial output for scan debug messages

### OLED display blank
- Check I2C wiring (SDA/SCL)
- Verify OLED address (usually 0x3C)
- Test with simple display code first

### Main controller not responding
- Check that ESPNowRemote initialized properly
- Verify action bindings match expected action names
- Watch serial console for received messages

## Customization

### Changing Key Mappings

Edit `remote_device/main.py` in the `layers` dictionary:

```python
self.layers = {
    0: {
        '2': 'aimer_up',
        # ... modify as needed
    },
}
```

### Adding New Actions

1. Add action to Magnus class in `esp_app/magnus.py`
2. Bind action in Magnus.__init__:
   ```python
   self.remote.bind("my_new_action", self.my_method)
   ```
3. Add to remote layer configuration in `remote_device/main.py`
4. Update label_map for display

### Adjusting Sleep Timeout

In `remote_device/main.py`:
```python
INACTIVITY_TIMEOUT = 60  # Change to desired seconds
```

## Advanced Configuration

### Power Optimization

For longer battery life:
- Reduce status update frequency (increase sleep time in status_update_loop)
- Implement wake-on-press using ESP32 deep sleep with GPIO wake
- Use lower OLED brightness (requires hardware modification)

### Range Extension

- Use external antenna on ESP32 boards with U.FL connector
- Position devices with clear line of sight
- Avoid metal enclosures that block signal

## License

Same as RoboPong main project.
