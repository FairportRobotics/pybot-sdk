import magicbot
from xrp import XRPServo


class XRPServo:
    the_servo: XRPServo

    def setup(self):
        self._position = self.the_servo.getPosition()

    def execute(self):
        self.the_servo.setPosition(self.position)

    @magicbot.feedback(key="position")
    def get_position(self) -> float:
        return self.the_servo.getPosition()

    @property
    def position(self) -> float:
        return self._position

    @position.setter
    def position(self, value) -> None:
        # Make sure the position is between 0 and 1
        self._position = max(0.0, min(1.0, value))