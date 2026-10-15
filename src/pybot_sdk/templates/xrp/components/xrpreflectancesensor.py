"""XRP Reflectance Sensor component."""

import magicbot
import xrp


class XRPReflectanceSensor:
    """Reflectance sensor component for the XRP robot."""

    # Injected variables
    sensor: xrp.XRPReflectanceSensor
    threshold: float = 0.5
    line_on_left = False
    line_on_right = False

    def setup(self) -> None:
        """Set up the reflectance sensor component."""
        self._raw_left = 0.0
        self._raw_right = 0.0

    def execute(self) -> None:
        """Run the component's periodic behavior."""
        self._raw_left = self.sensor.getLeftReflectanceValue()
        self._raw_right = self.sensor.getRightReflectanceValue()
        self.line_on_left = self._raw_left <= self.threshold
        self.line_on_right = self._raw_right <= self.threshold

    @magicbot.feedback(key="left reflectance")
    def _get_left_reflectance(self) -> float:
        """Return the left reflectance value."""
        return self._raw_left

    @magicbot.feedback(key="right reflectance")
    def _get_right_reflectance(self) -> float:
        """Return the right reflectance value."""
        return self._raw_right

    @magicbot.feedback(key="line on left")
    def _get_line_on_left(self) -> bool:
        """Return whether the line is detected on the left side."""
        return self.line_on_left

    @magicbot.feedback(key="line on right")
    def _get_line_on_right(self) -> bool:
        """Return whether the line is detected on the right side."""
        return self.line_on_right
