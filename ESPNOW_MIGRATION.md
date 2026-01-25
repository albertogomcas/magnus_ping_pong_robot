# ESP-NOW Remote Migration Summary

This document summarizes the changes made to replace the IR remote with an ESP-NOW based remote control.

## What Was Changed

### Main Controller (RoboPong ESP32)

#### 1. `esp_app/parts.py`
- **Added**: ESP-NOW imports (`espnow`, `network`, `json`)
- **Added**: New `ESPNowRemote` class that replaces the old UART-based `Remote` class
- **Features**:
  - Bidirectional ESP-NOW communication
  - Action binding system (compatible with old Remote interface)
  - Status broadcast capability for OLED feedback
  - Non-blocking message reception

#### 2. `esp_app/magnus.py`
- **Modified**: Import statement to include `ESPNowRemote`
- **Removed**: `UsedPins.REMOTE_RX = 27` (no longer needed)
- **Replaced**: `Remote(UsedPins.REMOTE_RX)` with `ESPNowRemote()`
- **Updated**: All action bindings to use new action names:
  - Layer 0: Aimer controls, toggle activation, feed one
  - Layer 1: Spin presets (9 directions + no spin + random)
  - Layer 2: Speed/spin/interval adjustments
- **Added**: `interval_up()` and `interval_down()` methods
- **Added**: Status callback for remote display updates

### Remote Device (New ESP32)

Created new directory: `esp_app/remote_device/`

#### 1. `main.py` - Remote Controller
- Main application loop
- Layer management (3 layers with 12 keys each)
- Battery monitoring and auto-sleep
- OLED display coordination
- ESP-NOW communication

#### 2. `keypad.py` - 3x4 Matrix Keypad Scanner
- Row/column scanning with debouncing
- Key mapping for standard phone keypad layout (123/456/789/*0#)
- Non-blocking scan method

#### 3. `oled_display.py` - SSD1306 OLED Driver
- UI rendering for 128x64 display
- Shows layer name, key labels, status, and battery voltage
- Visual feedback for key presses

#### 4. `espnow_sender.py` - ESP-NOW Communication
- Bidirectional message sending/receiving
- JSON message encoding
- MAC address management

#### 5. `get_mac.py` - Utility Script
- Helper to retrieve ESP32 MAC addresses
- Formats output for easy copy/paste into configuration

#### 6. Documentation Files
- `README.md` - Quick reference
- `SETUP_GUIDE.md` - Comprehensive setup instructions

## Key Mapping

### Layer 0 - CONTROL
```
  1    2↑   3
  4←   5⊙   6→
  7    8↓   9
  *    0    #

2 = Aim Up
4 = Aim Left
5 = Aim Center
6 = Aim Right
8 = Aim Down
0 = Feed One Ball
# = Start/Stop
* = Switch Layer
```

### Layer 1 - SPIN PRESETS
```
  1↖   2↑   3↗
  4←   5    6→
  7↙   8↓   9↘
  *    0    #

1-9 = Spin direction (TL, T, TR, L, Random, R, BL, B, BR)
0 = No Spin
# = Start/Stop
* = Switch Layer
```

### Layer 2 - SETTINGS
```
  1    2    3
  4    5    6
  7    8    9
  *    0    #

1 = Speed Up
3 = Speed Down
4 = Decrease Spin
6 = Increase Spin
7 = Interval Up
9 = Interval Down
# = Start/Stop
* = Switch Layer
```

## Hardware Requirements

### Remote Device
- ESP32 development board
- 3x4 matrix keypad (12 keys)
- 128x64 I2C OLED display (SSD1306)
- Battery pack (LiPo or AA batteries)
- Optional: Voltage divider for battery monitoring

### GPIO Assignments (Remote)
- Keypad Rows: GPIO 15, 2, 0
- Keypad Columns: GPIO 4, 16, 17, 5
- OLED SDA: GPIO 21
- OLED SCL: GPIO 22
- Battery Monitor: GPIO 35 (ADC)

## Setup Steps

1. **Get MAC Addresses**
   - Run `get_mac.py` on both ESP32 devices
   - Note the Station (STA) MAC addresses

2. **Configure MAC Address**
   - Edit `remote_device/main.py`
   - Set `RECEIVER_MAC` to main controller's MAC address

3. **Install ssd1306 Library**
   - Download from MicroPython repository
   - Upload to remote device

4. **Upload Firmware**
   - Main controller: Updated `parts.py` and `magnus.py`
   - Remote device: All files in `remote_device/`

5. **Test**
   - Power on both devices
   - Verify OLED displays Layer 0
   - Test key presses and layer switching

## Benefits of ESP-NOW Remote

1. **Wireless Range**: ~100m outdoors vs. IR's line-of-sight only
2. **Bidirectional**: Remote receives status updates for display
3. **Multiple Layers**: Access to all functions without mode confusion
4. **Visual Feedback**: OLED shows current settings and battery level
5. **Battery Powered**: Portable, no cables
6. **Auto Sleep**: Conserves battery when not in use
7. **Expandable**: Easy to add new actions and layers

## Backward Compatibility

The old `Remote` class is still present in `parts.py` for reference, but is no longer used. To revert to IR remote:

1. In `magnus.py`, change `ESPNowRemote()` back to `Remote(UsedPins.REMOTE_RX)`
2. Uncomment `UsedPins.REMOTE_RX = 27`
3. Restore old binding calls

## Future Enhancements

Possible improvements:
- Add preset storage on remote
- Implement sequence control from remote
- Add haptic feedback
- Create 3D-printable enclosure design
- Implement OTA firmware updates
- Add multiple remote support

## Testing Checklist

- [ ] Main controller boots and initializes ESP-NOW
- [ ] Remote device powers on and shows OLED display
- [ ] Key presses registered on remote
- [ ] Actions execute on main controller
- [ ] Layer switching works (* key)
- [ ] All aimer controls functional (Layer 0)
- [ ] All spin presets functional (Layer 1)
- [ ] Speed/interval controls functional (Layer 2)
- [ ] Status updates appear on OLED
- [ ] Battery voltage displays correctly
- [ ] Auto-sleep activates after timeout
- [ ] Wake from sleep on key press

## Troubleshooting

See `esp_app/remote_device/SETUP_GUIDE.md` for detailed troubleshooting steps.

## Files Changed/Added

### Modified Files
- `esp_app/parts.py` - Added ESPNowRemote class
- `esp_app/magnus.py` - Updated to use ESPNowRemote

### New Files
- `esp_app/remote_device/__init__.py`
- `esp_app/remote_device/main.py`
- `esp_app/remote_device/keypad.py`
- `esp_app/remote_device/oled_display.py`
- `esp_app/remote_device/espnow_sender.py`
- `esp_app/remote_device/get_mac.py`
- `esp_app/remote_device/README.md`
- `esp_app/remote_device/SETUP_GUIDE.md`
- `ESPNOW_MIGRATION.md` (this file)
