# ESP-NOW Remote Device

This directory contains firmware for the ESP32-C6 based remote control with 12-key matrix keypad and OLED display.

## Hardware

- **MCU**: ESP32-C6 (e.g., Nano ESP32-C6)
- **Keypad**: 4x3 matrix keypad (12 keys)
- **Display**: SSD1306 OLED 128x64 (with yellow title band)
- **Power**: Battery-powered with voltage monitoring

## Pin Connections

### Keypad (4x3 Matrix)
Physical pad order on keypad: Col2, Row1, Col1, Row4, Col3, Row3, Row2

```
Keypad Pad → ESP32-C6 GPIO
─────────────────────────────
Pad 1 (Col2) → GPIO 7
Pad 2 (Row1) → GPIO 2
Pad 3 (Col1) → GPIO 6
Pad 4 (Row4) → GPIO 5
Pad 5 (Col3) → GPIO 8
Pad 6 (Row3) → GPIO 4
Pad 7 (Row2) → GPIO 3
```

Summary:
- **Rows**: GPIO 2, 3, 4, 5 (consecutive)
- **Columns**: GPIO 6, 7, 8 (consecutive)

### OLED Display (I2C SSD1306 128x64)
- **SDA**: GPIO 21
- **SCL**: GPIO 22
- **I2C Frequency**: 400kHz

### Battery Monitoring
- **ADC Pin**: GPIO 0
- Requires voltage divider (e.g., 2:1) for battery voltage monitoring
- Range: 3.0V (empty) to 4.2V (full)

## Key Layout

```
1  2  3
4  5  6
7  8  9
*  0  #
```

## Layers

The remote has 3 layers accessible by pressing `*` (asterisk key).

### Layer 0 - AIM
Control the ball launcher aim and feeding.

- **2**: Aim Up
- **4**: Aim Left
- **5**: Aim Center
- **6**: Aim Right
- **8**: Aim Down
- **0**: Feed One Ball
- **#**: Start/Stop Launcher
- **\***: Switch Layer

### Layer 1 - SPIN
Set ball spin presets.

- **1-9**: Spin directions
  - 1: Top-Left, 2: Top, 3: Top-Right
  - 4: Left, 5: Random, 6: Right
  - 7: Bottom-Left, 8: Bottom/Backspin, 9: Bottom-Right
- **0**: Feed One Ball
- **#**: Start/Stop Launcher
- **\***: Switch Layer

### Layer 2 - SPEED
Adjust speed and timing settings.

- **1**: Speed Up
- **3**: Speed Down
- **4**: Decrease Spin Strength
- **6**: Increase Spin Strength
- **7**: Interval Up (time between balls)
- **9**: Interval Down (time between balls)
- **0**: Feed One Ball
- **#**: Start/Stop Launcher
- **\***: Switch Layer

## Display

The OLED display shows:
- **Yellow band** (top 16px): Current layer name (AIM/SPIN/SPEED) and battery indicator (5-bar graph)
- **White area**: 
  - Launcher status (ACTIVE/STANDBY)
  - Current speed percentage
  - Current spin angle

## Features

- **ESP-NOW Communication**: Low-latency wireless control
- **Battery Management**: 
  - Graphical battery indicator (5 bars)
  - Automatic deep sleep after 60 seconds of inactivity
  - Low power consumption
- **Three-Layer Interface**: Quick access to all controls
- **Debounced Keypad**: Reliable key detection with 200ms debounce

## Testing

### Test Keypad
Verify keypad wiring by displaying pressed keys on the OLED:
```python
# In main.py, uncomment:
test_keypad()
```
Press `*` three times to exit the test.

### Test Display
Test OLED display with all UI elements:
```python
# In main.py, uncomment:
demo_display()
```

### Run Remote Controller
```python
# In main.py, uncomment:
main()
```

## Configuration

1. **Set Receiver MAC Address**: Update `RECEIVER_MAC` in `main.py` with the MAC address of the main controller ESP32
2. **Adjust Battery Calibration**: Modify voltage divider ratio in `get_battery_voltage()` if needed
3. **Customize Inactivity Timeout**: Change `INACTIVITY_TIMEOUT` (default: 60 seconds)

## Required Files

- `main.py` - Main remote controller
- `keypad.py` - Matrix keypad driver (4x3)
- `oled_display.py` - OLED display driver
- `espnow_sender.py` - ESP-NOW communication
- `ssd1306.py` - MicroPython SSD1306 library
- `get_mac.py` - Utility to get device MAC address
- `secrets.py` - WiFi credentials (optional, for channel auto-detection)

## Installation

1. **Flash MicroPython** to ESP32-C6
   ```bash
   esptool.py --chip esp32c6 erase_flash
   esptool.py --chip esp32c6 write_flash -z 0x0 micropython.bin
   ```

2. **Upload Required Libraries**
   - Upload `ssd1306.py` (OLED driver)

3. **Upload Remote Device Files**
   - Upload all `.py` files from this directory

4. **Get MAC Address** (optional, for receiver configuration)
   ```python
   import get_mac
   ```

5. **Configure and Test**
   - Set `RECEIVER_MAC` in `main.py`
   - Run keypad test first: `test_keypad()`
   - Then run full remote: `main()`

## Troubleshooting

### "Invalid Pin" Error
- Ensure you're using ESP32-C6 compatible pins
- Current configuration uses GPIO 0-8, 21-22 (all valid for ESP32-C6)

### Keypad Not Responding
- Run `test_keypad()` to verify wiring
- Check that all row/column connections match the pin mapping

### Display Issues
- Run `demo_display()` to test OLED
- Verify I2C connections (SDA=21, SCL=22)
- Check I2C address (default: 0x3C)

### Battery Reading Incorrect
- Adjust voltage divider ratio in `get_battery_voltage()`
- Verify ADC connection on GPIO 0

## Power Consumption

- **Active**: ~80mA (display on, ESP-NOW active)
- **Idle**: ~20mA (display on, waiting for input)

To conserve battery, manually power off the remote when not in use.
