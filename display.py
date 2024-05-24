from machine import SoftI2C, Pin
import ssd1306
import asyncio

class Display:
    def __init__(self, sda, scl, width=128, height=32):
        i2c = SoftI2C(sda=Pin(sda), scl=Pin(scl))
        self._display = ssd1306.SSD1306_I2C(width, height, i2c)
        self._display.text("Starting up", 0, 0, 1)
        self._display.show()

        self._width = width
        self._height = height

        self._top = ""
        self._middle = ""
        self._bottom = ""

    def top(self, text):
        self._top = text

    def middle(self, text):
        self._middle = text

    def bottom(self, text):
        self._bottom = text

    def refresh(self):
        self._display.fill(0)
        self._display.text(self._top, 0, 0, 1)
        self._display.text(self._middle, 0, 10, 1)
        self._display.text(self._bottom, 0, 25, 1)
        self._display.show()

    async def auto_refresh(self):
        while True:
            self.refresh()
            await asyncio.sleep(0.2)