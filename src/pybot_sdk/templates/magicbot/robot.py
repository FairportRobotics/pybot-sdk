"""MagicBot robot template."""
import constants
from components import XboxController
from magicbot import MagicRobot


class Robot(MagicRobot):
    """MagicBot entry point."""

    controller: XboxController

    def createObjects(self) -> None:
        """Construct RobotPy objects before MagicBot injects the component."""
        self.controller = XboxController(port=constants.CONTROLLER_PORT)

    def teleopPeriodic(self) -> None:
        """Leave periodic behavior to the injected component's execute method."""
        pass
