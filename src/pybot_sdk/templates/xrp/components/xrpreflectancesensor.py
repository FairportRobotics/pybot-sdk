import xrp
import magicbot

class XRPReflectanceSensor:
    sensor: xrp.XRPReflectanceSensor
    threshold: float = 0.5
    line_on_left = False
    line_on_right = False
    

    def setup(self):
        self._raw_left = 0.0
        self._raw_right = 0.0

    def execute(self):
        self._raw_left = self.sensor.getLeftReflectanceValue()
        self._raw_right = self.sensor.getRightReflectanceValue()
        self.line_on_left = self._raw_left <= self.threshold
        self.line_on_right = self._raw_right <= self.threshold

    @magicbot.feedback(key="left reflectance")
    def _get_left_reflectance(self) -> float:
        return self._raw_left

    @magicbot.feedback(key="right reflectance")
    def _get_right_reflectance(self) -> float:
        return self._raw_right

    @magicbot.feedback(key="line on left")
    def _get_line_on_left(self) -> bool:
        return self.line_on_left

    @magicbot.feedback(key="line on right")
    def _get_line_on_right(self) -> bool:
        return self.line_on_right