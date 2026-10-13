from xrp import XRPOnBoardIO
from wpilib import Timer


class XRPLed:
    blink_time: float = 0.5
    mode: str = "on"
    led: XRPOnBoardIO

    def setup(self) -> None:
        self.led.setLed(True)
        self._timer = Timer()
        self._timer.start()

    def execute(self) -> None:
        if self.mode.lower() == "blink":
            if self._timer.hasElapsed(self.blink_time):
                self.led.setLed(not self.led.getLed())
                self._timer.reset()
        elif self.mode.lower() == "on":
            self.led.setLed(True)
        else:
            self.led.setLed(False)
