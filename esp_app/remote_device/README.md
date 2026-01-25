# ESP-NOW Remote Device

This directory contains firmware for the ESP32-based remote control.

## Hardware Setup

### Keypad Connections (3x4 Matrix)
- Row 1: GPIO 15
- Row 2: GPIO 2
- Row 3: GPIO 0
- Col 1: GPIO 4
- Col 2: GPIO 16
- Col 3: GPIO 17
- Col 4: GPIO 5

### OLED Display (I2C SSD1306)
- SDA: GPIO 21
- SCL: GPIO 22

### Battery Monitoring
- Battery voltage divider: GPIO 35 (ADC1_CH7)

## Key Layout

```
1  2  3
4  5  6
7  8  9
*  0  #
```

## Layers

### Layer 0 - Control
- 2: Aim Up
- 4: Aim Left
- 5: Aim Center
- 6: Aim Right
- 8: Aim Down
- 0: Feed One Ball
- #: Start/Stop
- *: Switch Layer

### Layer 1 - Spin Presets
- 1-9: Spin directions (TL, T, TR, L, Random, R, BL, B, BR)
- 0: No spin
- #: Start/Stop
- *: Switch Layer

### Layer 2 - Settings
- 1: Speed Up
- 3: Speed Down
- 4: Decrease Spin
- 6: Increase Spin
- 7: Interval Up
- 9: Interval Down
- #: Start/Stop
- *: Switch Layer

## Configuration

Update `RECEIVER_MAC` in `main.py` with the MAC address of the main controller ESP32.

## Required Libraries

- ssd1306.py (MicroPython OLED driver)

## Installation

1. Flash MicroPython to ESP32
2. Upload ssd1306.py library
3. Upload all files in this directory
4. Set main.py to run on boot
