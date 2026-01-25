"""
OLED Display Driver for SSD1306 128x64
"""
import ssd1306


class OLEDDisplay:
    def __init__(self, i2c):
        """Initialize OLED display"""
        self.oled = ssd1306.SSD1306_I2C(128, 64, i2c)
        self.width = 128
        self.height = 64
        self.oled.fill(0)
        self.oled.show()

    def clear(self):
        """Clear display"""
        self.oled.fill(0)
        self.oled.show()

    def draw_ui(self, layer_name, layer_num, key_labels, status, battery_voltage):
        """Draw main UI"""
        self.oled.fill(0)

        # Header: Layer name and battery
        self.oled.text(f"L{layer_num}:{layer_name}", 0, 0)
        batt_text = f"{battery_voltage:.1f}V"
        self.oled.text(batt_text, 128 - len(batt_text) * 8, 0)

        # Separator line
        self.oled.hline(0, 10, 128, 1)

        # Key grid - 3x4 layout
        # Display area: y=12 to y=48 (36 pixels for keys)
        keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']
        cell_width = 42
        cell_height = 9

        for i, key in enumerate(keys):
            row = i // 3
            col = i % 3
            x = col * cell_width
            y = 12 + row * cell_height

            label = key_labels.get(key, '')
            # Show key number and label
            text = f"{key}:{label[:4]}" if label else key
            self.oled.text(text, x + 2, y)

        # Status line separator
        self.oled.hline(0, 50, 128, 1)

        # Status info
        if status.get('launcher_active'):
            active_text = "ON"
        else:
            active_text = "OFF"

        speed = status.get('speed', 0)
        spin_angle = status.get('spin_angle', 0)

        status_text = f"{active_text} S:{speed:.0f} A:{spin_angle:.0f}"
        self.oled.text(status_text, 0, 54)

        self.oled.show()

    def flash_key(self, key):
        """Visual feedback for key press (can be enhanced)"""
        # For now, just update display
        pass

    def show_message(self, message):
        """Show a centered message"""
        self.oled.fill(0)
        x = (128 - len(message) * 8) // 2
        y = 28
        self.oled.text(message, x, y)
        self.oled.show()

    def show_battery_warning(self):
        """Show low battery warning"""
        # Add small indicator in corner
        self.oled.text("!", 120, 54)
        self.oled.show()
