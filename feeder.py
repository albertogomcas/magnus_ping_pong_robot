
from machine import Pin
import Stepper
import asyncio
class Feeder:
    """Uses a stepper to feed balls into the launcher"""
    def __init__(self, pins):
        self.pin1 = Pin(pins[0], Pin.OUT)
        self.pin2 = Pin(pins[1], Pin.OUT)
        self.pin3 = Pin(pins[2], Pin.OUT)
        self.pin4 = Pin(pins[3], Pin.OUT)

        self.stepper = Stepper.create(self.pin1, self.pin2, self.pin3, self.pin4, delay=5, mode="HALF_STEP")
        self.interval = 4
        self.active = False

    def set_ball_interval(self, seconds):
        self.interval = max(1, seconds)

    async def feed_one(self):
        await self.stepper.async_step(50, -1)

    async def run(self):
        while True:
            await asyncio.sleep(self.interval)
            if self.active:
                await self.feed_one()

    def activate(self):
        self.active = True

    def halt(self):
        self.active = False
        self.stepper.reset()
