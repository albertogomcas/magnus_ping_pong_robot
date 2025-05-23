# RoboPong

RoboPong is an automated table tennis (ping pong) robot that can launch balls with configurable speed, spin, and direction. It consists of an ESP32-based controller for the hardware components and a web interface for remote control.

## Table of Contents

- [Overview](#overview)
- [Project Architecture](#project-architecture)
- [Hardware Components](#hardware-components)
- [Software Components](#software-components)
- [Setup Instructions](#setup-instructions)
  - [ESP32 Setup](#esp32-setup)
  - [Web Interface Setup](#web-interface-setup)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [License](#license)

## Overview

RoboPong is designed to help table tennis players practice by automatically launching balls with various speeds, spins, and directions. The system consists of:

1. A ball launcher mechanism with three brushless motors
2. A ball feeding mechanism with a servo motor
3. An aiming mechanism with vertical and horizontal servos
4. An ESP32 microcontroller to control all components
5. A web interface for remote control

## Project Architecture

The project is organized into two main components:

1. **ESP32 Application (`esp_app/`)**: Controls the hardware components and provides a JSON-RPC API for remote control.
2. **Web Interface (`web_shiny/`)**: A Shiny-based web application that communicates with the ESP32 to control the robot.

## Hardware Components

The RoboPong hardware consists of:

- **Launcher**: Three brushless motors controlled by ESCs (Electronic Speed Controllers) to launch the ball with configurable speed and spin.
- **Feeder**: A servo motor that feeds balls into the launcher at configurable intervals.
- **Aimer**: Vertical and horizontal servos to aim the launcher in different directions.
- **Shaker**: A servo motor that stirs the balls to prevent jamming.
- **ESP32**: The microcontroller that controls all components and provides a web interface.

## Software Components

### ESP32 Application (`esp_app/`)

- **boot.py**: Initializes the ESP32, connects to WiFi, and loads boot settings.
- **main.py**: Entry point for the application, starts the web server and WebREPL.
- **webmain.py**: Implements the web server and JSON-RPC API.
- **parts.py**: Defines classes for the hardware components (Aimer, Feeder, Launcher, ESC, Shaker).
- **servo.py**: Implements the Servo class for controlling servo motors.
- **ujrpc.py**: Implements a JSON-RPC service for remote control.
- **dev.py**: Contains development flags for simulation mode.

### Web Interface (`web_shiny/`)

- **web_magnus.py**: Implements the Shiny web application for controlling the robot.
- **drill.py**: Implements drill patterns or exercises.
- **target.py**: Implements target tracking or selection.
- **trajectory.py**: Implements ball trajectory calculations.

## Setup Instructions

### ESP32 Setup

1. Install MicroPython on the ESP32.
2. Copy the contents of the `esp_app/` directory to the ESP32.
3. Create a `secrets.py` file with your WiFi credentials:
   ```python
   class Wifi:
       ssid = "your_ssid"
       password = "your_password"
   ```
4. Connect the hardware components according to the pin assignments in `webmain.py`.
5. Reset the ESP32 to start the application.

### Web Interface Setup

1. Install Python 3.7 or later.
2. Install the required packages:
   ```bash
   pip install -r web_shiny/requirements.txt
   ```
3. Run the web interface:
   ```bash
   cd web_shiny
   python web_magnus.py
   ```

## Usage

1. Power on the RoboPong robot.
2. Connect to the same WiFi network as the robot.
3. Open the web interface in a browser.
4. Use the interface to:
   - Configure the launcher speed, spin, and direction
   - Set the ball feeding interval
   - Activate/deactivate the launcher and feeder
   - Save and load presets
   - Calibrate the aiming mechanism

## API Documentation

The ESP32 provides a JSON-RPC API for remote control. The following methods are available:

- **status**: Returns the status of the robot.
- **feed_one**: Feeds one ball if the launcher is active.
- **calibrate_aim_zero**: Calibrates the aiming mechanism to the zero position.
- **sync_settings**: Synchronizes settings from the client.
- **reset**: Resets the ESP32.
- **interrupt**: Shuts down the web server.
- **enable_simulation**: Enables simulation mode.
- **disable_simulation**: Disables simulation mode.

## Testing

The project includes unit tests for the ESP32 application. See [tests/README.md](tests/README.md) for more information.

To run the tests:

```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.