"""XRP Servo component."""

import magicbot
from xrp import XRPServo


class XRPServo:
    """Servo component for the XRP robot."""

    # Injected variables
    the_servo: XRPServo

    def setup(self) -> None:
        """Set up the servo component."""
        self._position = self.the_servo.getPosition()

    def execute(self) -> None:
        """Run the component's periodic behavior."""
        self.the_servo.setPosition(self.position)

    @magicbot.feedback(key="position")
    def get_position(self) -> float:
        """Return the current position of the servo."""
        return self.the_servo.getPosition()

    @property
    def position(self) -> float:
        """Get the desired position of the servo."""
        return self._position

    @position.setter
    def position(self, value) -> None:
        """Set the desired position of the servo."""
        # Make sure the position is between 0 and 1
        self._position = max(0.0, min(1.0, value))
