"""Read target information from a Limelight camera.

Limelight sends its readings to NetworkTables. This component reads whether a
target is visible, how far it is from the center of the camera, its size, and
the camera's pipeline latency.

In a RobotPy MagicBot project, declare the component and optionally choose the
Limelight's NetworkTables name in ``createObjects``::

    from components.limelight import Limelight
    from magicbot import MagicRobot

    class Robot(MagicRobot):
        limelight: Limelight

        def createObjects(self):
            self.limelight_table_name = "limelight"

        def teleopPeriodic(self):
            if self.limelight.has_target:
                turn_error = self.limelight.horizontal_offset_degrees
                print(f"Target is {turn_error:.1f} degrees from center")

The NetworkTables name is usually ``"limelight"``. If your camera has a
different name, use that name instead. Horizontal offset is positive when the
target is to the right of the camera's center; vertical offset is positive when
the target is above the center. Target area is a percentage of the camera
image. Latency is the pipeline latency reported by the camera, in milliseconds.

Call ``set_pipeline(index)`` to select a pipeline configured on the camera.
Pipeline numbering starts at zero. The component updates its readings in
MagicBot's ``execute`` loop, so other robot code can read the latest values.
"""

from magicbot import feedback
from ntcore import NetworkTableInstance


class Limelight:
    """Read target measurements from a Limelight using NetworkTables."""

    # Injected variables
    table_name: str = "limelight"

    def setup(self) -> None:
        """Find the camera's NetworkTables entries and initialize readings."""
        table = NetworkTableInstance.getDefault().getTable(self.table_name)
        self._target_valid_entry = table.getEntry("tv")
        self._horizontal_offset_entry = table.getEntry("tx")
        self._vertical_offset_entry = table.getEntry("ty")
        self._target_area_entry = table.getEntry("ta")
        self._pipeline_latency_entry = table.getEntry("tl")
        self._pipeline_entry = table.getEntry("pipeline")

        self.has_target = False
        self.horizontal_offset_degrees = 0.0
        self.vertical_offset_degrees = 0.0
        self.target_area_percent = 0.0
        self.pipeline_latency_ms = 0.0

    def execute(self) -> None:
        """Update the camera readings once each robot loop."""
        # Limelight uses tv=1 when it sees a target, and tv=0 when it does not.
        self.has_target = self._target_valid_entry.getDouble(0.0) == 1.0
        self.horizontal_offset_degrees = self._horizontal_offset_entry.getDouble(0.0)
        self.vertical_offset_degrees = self._vertical_offset_entry.getDouble(0.0)
        self.target_area_percent = self._target_area_entry.getDouble(0.0)
        self.pipeline_latency_ms = self._pipeline_latency_entry.getDouble(0.0)

    def set_pipeline(self, pipeline_index: int) -> None:
        """Tell Limelight to use a configured pipeline, numbered from zero.

        Raises:
            ValueError: If ``pipeline_index`` is negative.

        """
        if pipeline_index < 0:
            raise ValueError("pipeline_index must be zero or greater")
        self._pipeline_entry.setDouble(pipeline_index)

    @feedback
    def target_found(self) -> bool:
        """Show whether the camera currently sees a target in MagicBot."""
        return self.has_target

    @feedback
    def horizontal_offset(self) -> float:
        """Show the horizontal target offset in degrees in MagicBot."""
        return self.horizontal_offset_degrees

    @feedback
    def vertical_offset(self) -> float:
        """Show the vertical target offset in degrees in MagicBot."""
        return self.vertical_offset_degrees

    @feedback
    def target_area(self) -> float:
        """Show the target's image area as a percentage in MagicBot."""
        return self.target_area_percent

    @feedback
    def pipeline_latency(self) -> float:
        """Show Limelight's pipeline latency in milliseconds in MagicBot."""
        return self.pipeline_latency_ms
