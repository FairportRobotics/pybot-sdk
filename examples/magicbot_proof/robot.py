import wpilib
from magicbot import MagicRobot


class Drive:
    controller: wpilib.XboxController
    motor: wpilib.PWMSparkMax

    def execute(self) -> None:
        self.motor.set(self.controller.getLeftY())


class Robot(MagicRobot):
    drive: Drive

    def createObjects(self) -> None:
        self.controller = wpilib.XboxController(0)
        self.motor = wpilib.PWMSparkMax(0)

    def teleopPeriodic(self) -> None:
        pass