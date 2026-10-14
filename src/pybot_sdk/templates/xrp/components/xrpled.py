from xrp import XRPOnBoardIO
from wpilib import Timer


class XRPLed:
    blink_time: float = 0.5
    mode: str = "on"
    the_led: XRPOnBoardIO

    def setup(self) -> None:
        self.the_led.setLed(True)
        self._timer = Timer()
        self._timer.start()

    def execute(self) -> None:
        if self.mode.lower() == "blink":
            if self._timer.hasElapsed(self.blink_time):
                self.the_led.setLed(not self.the_led.getLed())
                self._timer.reset()
        elif self.mode.lower() == "on":
            self.the_led.setLed(True)
        else:
            self.the_led.setLed(False)
