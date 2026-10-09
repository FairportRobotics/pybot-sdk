"""Minimal RobotPy 2026 MagicBot lifecycle proof."""

import wpilib
from magicbot import MagicRobot


class Drive:
    """Forward Xbox left-stick input to a simulated PWM output."""

    controller: wpilib.XboxController
    motor: wpilib.PWMSparkMax

    def execute(self) -> None:
        """Write the current controller axis to the motor."""
        self.motor.set(self.controller.getLeftY())


class Robot(MagicRobot):
    """Proof robot using the normal MagicBot lifecycle."""

    drive: Drive

    def createObjects(self) -> None:
        """Construct the controller and logic-simulation output."""
        self.controller = wpilib.XboxController(0)
        self.motor = wpilib.PWMSparkMax(0)

    def teleopPeriodic(self) -> None:
        """Leave periodic behavior to the MagicBot component."""
        pass
