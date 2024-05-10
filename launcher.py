class Launcher:
    """Shoots balls using 3 brushless motors"""
    pass

    def activate(self):
        """Accelerate towards launching speed"""
        pass

    def ease(self):
        """Decelerate towards idle speed"""
        pass

    def halt(self):
        """Turn off"""
        pass

    def set_speed(self, speed_percent: int):
        """Sets speed of the launched ball"""
        pass

    def set_spin(self, top:float, right:float):
        """Sets spin of the ball negative (top == backspin)"""
        pass

