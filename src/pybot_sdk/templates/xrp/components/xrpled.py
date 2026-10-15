"""XRP LED Component."""

from wpilib import Timer
from xrp import XRPOnBoardIO


class XRPLed:
    """LED component for the XRP robot."""

    # Injected variables
    blink_time: float = 0.5
    mode: str = "on"
    the_led: XRPOnBoardIO

    def setup(self) -> None:
        """Set up the LED component."""
        self.the_led.setLed(True)
        self._timer = Timer()
        self._timer.start()

    def execute(self) -> None:
        """Run the component's periodic behavior."""
        if self.mode.lower() == "blink":
            if self._timer.hasElapsed(self.blink_time):
                self.the_led.setLed(not self.the_led.getLed())
                self._timer.reset()
        elif self.mode.lower() == "on":
            self.the_led.setLed(True)
        else:
            self.the_led.setLed(False)
