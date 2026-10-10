"""Command based robot template."""
import commands2
import constants
import wpilib
from robotcontainer import RobotContainer


class MyRobot(commands2.TimedCommandRobot):
    """Command based robot entry point."""

    def robotInit(self) -> None:
        """Robot initialization function."""
        self.container = RobotContainer()
        self.controller = wpilib.XboxController(constants.CONTROLLER_PORT)
        self.autonomous_command: commands2.Command | None = None

    def robotPeriodic(self) -> None:
        """Run the command scheduler."""
        # TimedCommandRobot runs the CommandScheduler automatically
        pass

    def disabledInit(self) -> None:
        """Initialize the disabled mode."""
        pass

    def autonomousInit(self) -> None:
        """Initialize autonomous mode by scheduling the autonomous command."""
        self.autonomous_command = self.container.get_autonomous_command()
        if self.autonomous_command:
            self.autonomous_command.schedule()

    def teleopInit(self) -> None:
        """Leave periodic behavior to the command scheduler."""
        if self.autonomous_command:
            self.autonomous_command.cancel()

    def testInit(self) -> None:
        """Initialize test mode by canceling all running commands."""
        commands2.CommandScheduler.getInstance().cancelAll()


if __name__ == "__main__":
    wpilib.run(MyRobot)
