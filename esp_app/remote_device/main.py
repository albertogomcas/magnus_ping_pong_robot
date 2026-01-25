"""
ESP-NOW Remote Control for RoboPong
Main controller for battery-powered remote with 3x4 keypad and OLED display
"""
import time
from machine import Pin, I2C, ADC, deepsleep
import asyncio

from keypad import Keypad
from oled_display import OLEDDisplay
from espnow_sender import ESPNowSender

# Configuration
RECEIVER_MAC = b'\xff\xff\xff\xff\xff\xff'  # TODO: Replace with actual receiver MAC address
INACTIVITY_TIMEOUT = 60  # seconds before sleep
LOW_BATTERY_THRESHOLD = 3.3  # volts

class RemoteController:
    def __init__(self):
        # Initialize components
        self.keypad = Keypad(
            row_pins=[15, 2, 0],     # GPIO pins for rows
            col_pins=[4, 16, 17, 5]  # GPIO pins for columns
        )

        # I2C for OLED (using different pins than ST servo on main controller)
        self.i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
        self.display = OLEDDisplay(self.i2c)

        # ESP-NOW sender
        self.sender = ESPNowSender(RECEIVER_MAC)

        # Battery monitoring
        self.battery_adc = ADC(Pin(35))
        self.battery_adc.atten(ADC.ATTN_11DB)  # 0-3.6V range

        # State
        self.current_layer = 0
        self.last_activity = time.time()
        self.status = {
            'launcher_active': False,
            'speed': 0,
            'topspin': 0,
            'sidespin': 0,
            'spin_angle': 0,
            'spin_strength': 0,
            'tilt': 0,
            'pan': 0,
        }

        # Layer definitions: key -> action_name
        self.layers = {
            0: {  # Control layer
                '2': 'aimer_up',
                '4': 'aimer_left',
                '5': 'aimer_center',
                '6': 'aimer_right',
                '8': 'aimer_down',
                '0': 'feed_one',
                '#': 'toggle_activation',
                '*': 'layer_switch',
            },
            1: {  # Spin presets layer
                '1': 'spin_TL',
                '2': 'spin_T',
                '3': 'spin_TR',
                '4': 'spin_L',
                '5': 'spin_random',
                '6': 'spin_R',
                '7': 'spin_BL',
                '8': 'spin_B',
                '9': 'spin_BR',
                '0': 'no_spin',
                '*': 'layer_switch',
                '#': 'toggle_activation',
            },
            2: {  # Speed/settings layer
                '1': 'speed_up',
                '3': 'speed_down',
                '4': 'decrease_spin',
                '6': 'increase_spin',
                '7': 'interval_up',
                '9': 'interval_down',
                '*': 'layer_switch',
                '#': 'toggle_activation',
            },
        }

        self.layer_names = {
            0: 'CONTROL',
            1: 'SPIN',
            2: 'SETTINGS',
        }

    def get_battery_voltage(self):
        """Read battery voltage"""
        raw = self.battery_adc.read()
        # Assuming voltage divider 2:1
        voltage = (raw / 4095.0) * 3.6 * 2
        return voltage

    def check_battery(self):
        """Check if battery is low"""
        voltage = self.get_battery_voltage()
        return voltage < LOW_BATTERY_THRESHOLD

    def switch_layer(self):
        """Cycle through layers"""
        self.current_layer = (self.current_layer + 1) % len(self.layers)
        print(f"[Remote] Switched to layer {self.current_layer}")
        self.update_display()

    def handle_key(self, key):
        """Handle keypress"""
        print(f"[Remote] Key pressed: {key}")
        self.last_activity = time.time()

        # Get action for this key in current layer
        action = self.layers[self.current_layer].get(key)

        if action == 'layer_switch':
            self.switch_layer()
            return

        if action:
            # Send key press to receiver
            message = {
                'type': 'key_press',
                'layer': self.current_layer,
                'key': key,
                'action': action,
                'timestamp': time.time(),
            }
            self.sender.send(message)
            print(f"[Remote] Sent action: {action}")

            # Visual feedback
            self.display.flash_key(key)
        else:
            print(f"[Remote] No action bound for key {key}")

    def update_display(self):
        """Update OLED display"""
        battery_voltage = self.get_battery_voltage()
        layer_name = self.layer_names[self.current_layer]
        key_labels = self.get_current_key_labels()

        self.display.draw_ui(
            layer_name=layer_name,
            layer_num=self.current_layer,
            key_labels=key_labels,
            status=self.status,
            battery_voltage=battery_voltage,
        )

    def get_current_key_labels(self):
        """Get abbreviated labels for current layer keys"""
        layer = self.layers[self.current_layer]

        # Map actions to short labels
        label_map = {
            'aimer_up': '↑',
            'aimer_down': '↓',
            'aimer_left': '←',
            'aimer_right': '→',
            'aimer_center': '⊙',
            'feed_one': 'FEED',
            'toggle_activation': 'START',
            'layer_switch': 'LAYER',
            'spin_TL': '↖',
            'spin_T': 'TOP',
            'spin_TR': '↗',
            'spin_L': 'LEFT',
            'spin_R': 'RIGHT',
            'spin_BL': '↙',
            'spin_B': 'BACK',
            'spin_BR': '↘',
            'spin_random': 'RND',
            'no_spin': 'NONE',
            'speed_up': 'SPD+',
            'speed_down': 'SPD-',
            'increase_spin': 'SPN+',
            'decrease_spin': 'SPN-',
            'interval_up': 'INT+',
            'interval_down': 'INT-',
        }

        # Create 3x4 grid of labels
        keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']
        labels = {}
        for key in keys:
            action = layer.get(key, '')
            labels[key] = label_map.get(action, '')

        return labels

    def check_inactivity(self):
        """Check if should enter deep sleep"""
        if time.time() - self.last_activity > INACTIVITY_TIMEOUT:
            print("[Remote] Inactivity timeout, entering deep sleep")
            self.display.clear()
            self.display.show_message("Sleeping...")
            time.sleep(0.5)
            # Configure wake on any keypad pin
            # deepsleep will wake on GPIO activity
            deepsleep()

    async def request_status(self):
        """Request status update from receiver"""
        message = {
            'type': 'status_request',
            'timestamp': time.time(),
        }
        self.sender.send(message)

    async def status_update_loop(self):
        """Periodically request status updates"""
        while True:
            await self.request_status()
            await asyncio.sleep(2)  # Request status every 2 seconds

    async def status_receiver_loop(self):
        """Receive status updates from main controller"""
        while True:
            status = self.sender.receive()
            if status and status.get('type') == 'status_response':
                self.status.update(status)
                self.update_display()
            await asyncio.sleep(0.1)

    async def keypad_loop(self):
        """Main keypad scanning loop"""
        while True:
            key = self.keypad.scan()
            if key:
                self.handle_key(key)
                # Debounce
                await asyncio.sleep(0.2)

            # Check inactivity
            self.check_inactivity()

            # Check battery
            if self.check_battery():
                self.display.show_battery_warning()

            await asyncio.sleep(0.05)

    async def run(self):
        """Main run loop"""
        print("[Remote] Starting remote controller")

        # Initial display
        self.update_display()

        # Start tasks
        keypad_task = asyncio.create_task(self.keypad_loop())
        status_update_task = asyncio.create_task(self.status_update_loop())
        status_receiver_task = asyncio.create_task(self.status_receiver_loop())

        await asyncio.gather(keypad_task, status_update_task, status_receiver_task)


def main():
    """Entry point"""
    print("[Remote] RoboPong Remote Control")
    print("[Remote] Initializing...")

    try:
        remote = RemoteController()
        asyncio.run(remote.run())
    except Exception as e:
        print(f"[Remote] Error: {e}")
        import sys
        sys.print_exception(e)

if __name__ == '__main__':
    main()
