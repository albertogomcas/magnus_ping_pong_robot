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
        """Draw main UI with layer-specific information"""
        self.oled.fill(0)

        # Yellow band (top 16 pixels): Layer name + status symbol
        self.oled.text(layer_name, 0, 4)

        # Status symbol (▶ for active, ■ for standby) next to layer name
        status_symbol = '>>>' if status.get('launcher_active') else 'STP'
        self.oled.text(status_symbol, 42, 4)

        # Battery indicator on right side of title
        self._draw_battery_indicator(battery_voltage, 98, 3)

        # Separator line (just below yellow band)
        self.oled.hline(0, 16, 128, 1)

        # Main content area (white area: y=18 to y=63)
        # Show different information based on layer

        if layer_num == 0:  # AIM layer
            self._draw_aim_info(status)
        elif layer_num == 1:  # SPIN layer
            self._draw_spin_info(status)
        elif layer_num == 2:  # SPEED layer
            self._draw_speed_info(status)

        self.oled.show()

    def _draw_aim_info(self, status):
        """Draw aimer information (Layer 0: AIM)"""
        y_pos = 24

        # Vertical aim (tilt)
        tilt = status.get('tilt', 0)
        self.oled.text(f"Vert: {tilt:.1f}", 0, y_pos)

        # Horizontal aim (pan)
        y_pos += 12
        pan = status.get('pan', 0)
        self.oled.text(f"Horiz: {pan:.1f}", 0, y_pos)


    def _draw_spin_info(self, status):
        """Draw spin information (Layer 1: SPIN)"""
        y_pos = 24

        # Spin angle
        spin_angle = status.get('spin_angle', 0)
        self.oled.text(f"Angle: {spin_angle}", 0, y_pos)

        # Spin strength (percentage)
        y_pos += 12
        spin_strength = status.get('spin_strength', 0)
        self.oled.text(f"Spin: {spin_strength:.0f}%", 0, y_pos)

    def _draw_speed_info(self, status):
        """Draw speed/settings information (Layer 2: SPEED)"""
        y_pos = 24

        # Launcher speed
        speed = status.get('speed', 0)
        self.oled.text(f"Launch: {speed}%", 0, y_pos)

        # Spin strength
        y_pos += 12
        spin_strength = status.get('spin_strength', 0)
        self.oled.text(f"Spin: {spin_strength:.0f}%", 0, y_pos)

        # Feed interval
        y_pos += 12
        interval = status.get('interval', 0)
        self.oled.text(f"Interval: {interval:.1f}s", 0, y_pos)

    def _draw_battery_indicator(self, voltage, x, y):
        """Draw battery level indicator with bars"""
        # Battery outline (24x10 pixels)
        width = 24
        height = 10

        # Draw battery body rectangle
        self.oled.rect(x, y, width, height, 1)

        # Draw battery terminal (small nub on right)
        self.oled.fill_rect(x + width, y + 3, 2, 4, 1)

        # Calculate battery level (3.0V = empty, 4.2V = full)
        min_voltage = 3.0
        max_voltage = 4.2
        level = (voltage - min_voltage) / (max_voltage - min_voltage)
        level = max(0, min(1, level))  # Clamp between 0 and 1

        # Draw bars (5 bars max, each 3 pixels wide with 1 pixel spacing)
        num_bars = 5
        bar_width = 3
        bar_spacing = 1
        filled_bars = int(level * num_bars + 0.5)

        for i in range(filled_bars):
            bar_x = x + 2 + i * (bar_width + bar_spacing)
            bar_y = y + 2
            bar_h = height - 4
            self.oled.fill_rect(bar_x, bar_y, bar_width, bar_h, 1)

    def flash_key(self, key):
        """Visual feedback for key press (can be enhanced)"""
        # For now, just update display
        pass

    def show_message(self, message):
        """Show a centered message"""
        self.oled.fill(0)
        # Center message in main area (below yellow band)
        x = (128 - len(message) * 8) // 2
        y = 32
        self.oled.text(message, x, y)
        self.oled.show()
