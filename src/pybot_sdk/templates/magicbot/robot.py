"""Student robot example using generated identifiers and standard RobotPy APIs."""

import wpilib
from hardware_map import CONTROLLERS
from magicbot import MagicRobot


class Drive:
    """MagicBot component that forwards the driver's left-stick input."""

    controller: wpilib.XboxController
    motor: wpilib.PWMSparkMax

    def execute(self) -> None:
        """Apply the current controller input to the simulated motor output."""
        self.motor.set(self.controller.getLeftY())


class Robot(MagicRobot):
    """MagicBot entry point for the starter project."""

    drive: Drive

    def createObjects(self) -> None:
        """Construct RobotPy objects before MagicBot injects the component."""
        self.controller = wpilib.XboxController(CONTROLLERS["driver"]["port"])
        self.motor = wpilib.PWMSparkMax(0)

    def teleopPeriodic(self) -> None:
        """Leave periodic behavior to the injected component's execute method."""
        pass
