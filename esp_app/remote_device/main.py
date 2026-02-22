"""
ESP-NOW Remote Control for RoboPong
Main controller for battery-powered remote with 3x4 keypad and OLED display
"""
import time
from machine import Pin, I2C, ADC
import asyncio

from keypad import Keypad
from oled_display import OLEDDisplay
from espnow_sender import ESPNowSender

# Try to import WiFi credentials
try:
    from secrets import Wifi
    WIFI_AVAILABLE = True
except ImportError:
    print("[Remote] Warning: No secrets.py found, WiFi auto-detection disabled")
    WIFI_AVAILABLE = False
    class Wifi:
        ssid = None
        password = None

# Configuration
RECEIVER_MAC = b'\xb0\xa7\x32\x32\x73\x1c'  # TODO: Replace with actual receiver MAC address
LOW_BATTERY_THRESHOLD = 3.3  # volts

class RemoteController:
    def __init__(self):
        # Initialize components
        # ESP32-C6 Keypad physical pin order: Col2, Row1, Col1, Row4, Col3, Row3, Row2
        # Wiring for easy connection (consecutive pins):
        #   Pad 1 (Col2) → GPIO 7
        #   Pad 2 (Row1) → GPIO 2
        #   Pad 3 (Col1) → GPIO 6
        #   Pad 4 (Row4) → GPIO 5
        #   Pad 5 (Col3) → GPIO 8
        #   Pad 6 (Row3) → GPIO 4
        #   Pad 7 (Row2) → GPIO 3
        self.keypad = Keypad(
            row_pins=[2, 3, 4, 5],       # GPIO for Row1, Row2, Row3, Row4 (consecutive)
            col_pins=[6, 7, 8]           # GPIO for Col1, Col2, Col3 (consecutive)
        )

        # I2C for OLED (using different pins than ST servo on main controller)
        self.i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
        self.display = OLEDDisplay(self.i2c)

        # ESP-NOW sender - auto-detect channel from WiFi connection
        # If WiFi credentials are available, connect briefly to get the channel
        # then disconnect and use that channel for ESP-NOW
        if WIFI_AVAILABLE and Wifi.ssid:
            print(f"[Remote] Auto-detecting WiFi channel from network: {Wifi.ssid}")
            self.sender = ESPNowSender(
                RECEIVER_MAC,
                wifi_ssid=Wifi.ssid,
                wifi_password=Wifi.password
            )
        else:
            print(f"[Remote] No WiFi credentials, using default channel 1")
            print(f"[Remote] Create secrets.py with WiFi credentials for auto-detection")
            self.sender = ESPNowSender(RECEIVER_MAC, channel=1)

        # Battery monitoring (ESP32-C6: ADC on GPIO 0)
        self.battery_adc = ADC(Pin(0))
        self.battery_adc.atten(ADC.ATTN_11DB)  # Full range

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
            'interval': 4.0,
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
                '5': 'no_spin',
                '6': 'spin_R',
                '7': 'spin_BL',
                '8': 'spin_B',
                '9': 'spin_BR',
                '0': 'feed_one',
                '*': 'layer_switch',
                '#': 'toggle_activation',
            },
            2: {  # Speed/settings layer
                '1': 'speed_down',
                '3': 'speed_up',
                '4': 'decrease_spin',
                '6': 'increase_spin',
                '7': 'interval_up',
                '9': 'interval_down',
                '0': 'feed_one',
                '*': 'layer_switch',
                '#': 'toggle_activation',
            },
        }

        self.layer_names = {
            0: 'AIM',
            1: 'SPIN',
            2: 'SPEED',
        }

    def get_battery_voltage(self):
        """Read battery voltage"""
        raw = self.battery_adc.read()
        # Assuming voltage divider 2:1
        voltage = (raw / 4095.0) * 3.3 * 2
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

    def handle_key(self, key, press_type='short'):
        """Handle keypress

        press_type: 'short' or 'long' - determines adjustment magnitude
        """
        print(f"[Remote] Key pressed: {key} ({press_type})")

        # Get action for this key in current layer
        action = self.layers[self.current_layer].get(key)

        if action == 'layer_switch':
            self.switch_layer()
            return

        if action:
            # Send key press to receiver with press type
            message = {
                'type': 'key_press',
                'layer': self.current_layer,
                'key': key,
                'action': action,
                'press_type': press_type,
                'timestamp': time.time(),
            }
            self.sender.send(message)
            print(f"[Remote] Sent action: {action} ({press_type})")

            # Visual feedback
            self.display.flash_key(key)

            # Request immediate status update to get real values from robot
            asyncio.create_task(self.request_status())
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
            await asyncio.sleep(1)  # Request status every 1 second for faster sync

    async def status_receiver_loop(self):
        """Receive status updates from main controller"""
        print("[Remote] Status receiver loop started")
        msg_count = 0
        while True:
            status = self.sender.receive()
            if status:
                msg_count += 1
                print(f"[Remote] Received status #{msg_count}: type={status.get('type')}")
                if status.get('type') == 'status_response':
                    print(f"[Remote] Status data: speed={status.get('speed')}, launcher_active={status.get('launcher_active')}")
                    self.status.update(status)
                    print(f"[Remote] Updated internal status: {self.status}")
                    self.update_display()
                else:
                    print(f"[Remote] Ignoring message with type: {status.get('type')}")
            await asyncio.sleep(0.05)  # Faster polling for quicker status updates

    async def keypad_loop(self):
        """Main keypad scanning loop"""
        while True:
            key, press_type = self.keypad.scan()
            if key and press_type:
                self.handle_key(key, press_type)

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


def test_keypad():
    """Test keypad by displaying pressed keys on OLED"""
    print("[Test] Keypad Test - Press keys to see them on display")
    print("[Test] Press * three times to exit")

    # Initialize components
    keypad = Keypad(
        row_pins=[2, 3, 4, 5],
        col_pins=[6, 7, 8]
    )

    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    display = OLEDDisplay(i2c)

    # Show initial message
    display.oled.fill(0)
    display.oled.text("Keypad Test", 20, 0)
    display.oled.text("Press any key", 12, 20)
    display.oled.text("* x3 to exit", 16, 40)
    display.oled.show()

    star_count = 0
    last_keys = []  # Keep history of last 5 keys

    while star_count < 3:
        key = keypad.scan()
        if key:
            print(f"[Test] Key pressed: {key}")

            # Count consecutive star presses for exit
            if key == '*':
                star_count += 1
            else:
                star_count = 0

            # Add to history
            last_keys.append(key)
            if len(last_keys) > 5:
                last_keys.pop(0)

            # Display the pressed key
            display.oled.fill(0)
            display.oled.text("Keypad Test", 20, 0)
            display.oled.hline(0, 12, 128, 1)

            # Show current key (large)
            display.oled.text(f"Key: {key}", 40, 20)

            # Show key history
            display.oled.text("History:", 0, 40)
            history_str = ' '.join(last_keys)
            display.oled.text(history_str, 0, 52)

            display.oled.show()

            # Debounce delay
            time.sleep(0.3)

    # Exit message
    display.oled.fill(0)
    display.oled.text("Test Complete!", 16, 28)
    display.oled.show()
    time.sleep(1)
    display.clear()
    print("[Test] Keypad test complete!")


def demo_display():
    """Demo code to test OLED display - comment out when not needed"""
    print("[Demo] Testing OLED Display")

    # Initialize I2C and display
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    display = OLEDDisplay(i2c)

    # Test 1: Show welcome message
    print("[Demo] Test 1: Welcome message")
    display.show_message("RoboPong!")
    time.sleep(2)

    # Test 2: Draw full UI for each layer
    layers = ['AIM', 'SPIN', 'SPEED']

    # Sample key labels for each layer
    layer_labels = [
        # Layer 0: Control
        {'1': '', '2': '↑', '3': '', '4': '←', '5': '⊙', '6': '→',
         '7': '', '8': '↓', '9': '', '*': 'LAYR', '0': 'FEED', '#': 'STRT'},
        # Layer 1: Spin
        {'1': '↖', '2': 'TOP', '3': '↗', '4': 'LEFT', '5': 'RND', '6': 'RGHT',
         '7': '↙', '8': 'BACK', '9': '↘', '*': 'LAYR', '0': 'NONE', '#': 'STRT'},
        # Layer 2: Settings
        {'1': 'SPD+', '2': '', '3': 'SPD-', '4': 'SPN-', '5': '', '6': 'SPN+',
         '7': 'INT+', '8': '', '9': 'INT-', '*': 'LAYR', '0': 'FEED', '#': 'STRT'},
    ]

    status = {
        'launcher_active': False,
        'speed': 50,
        'spin_angle': 45,
    }

    for i, layer_name in enumerate(layers):
        print(f"[Demo] Test {i+1}: Layer {i} - {layer_name}")
        display.draw_ui(
            layer_name=layer_name,
            layer_num=i,
            key_labels=layer_labels[i],
            status=status,
            battery_voltage=3.7,
        )
        time.sleep(3)

        # Toggle launcher active for second iteration
        if i == 1:
            status['launcher_active'] = True
            print(f"[Demo] Test {i+1}b: Layer {i} with launcher ON")
            display.draw_ui(
                layer_name=layer_name,
                layer_num=i,
                key_labels=layer_labels[i],
                status=status,
                battery_voltage=3.7,
            )
            time.sleep(3)

    # Test: Low battery indicator (shows fewer bars)
    print("[Demo] Test: Low battery indicator")
    display.draw_ui(
        layer_name='AIM',
        layer_num=0,
        key_labels=layer_labels[0],
        status={'launcher_active': False, 'speed': 30, 'spin_angle': 0},
        battery_voltage=3.2,
    )
    time.sleep(3)

    # Test: Full battery indicator
    print("[Demo] Test: Full battery indicator")
    display.draw_ui(
        layer_name='AIM',
        layer_num=0,
        key_labels=layer_labels[0],
        status={'launcher_active': False, 'speed': 30, 'spin_angle': 0},
        battery_voltage=4.1,
    )
    time.sleep(3)

    # Clear and finish
    display.clear()
    print("[Demo] Display test complete!")


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
    # Uncomment ONE of the following to test:

    # Test keypad (shows pressed keys on display):
    #test_keypad()

    # Test display only:
    #demo_display()

    # Run main remote controller:
    main()
