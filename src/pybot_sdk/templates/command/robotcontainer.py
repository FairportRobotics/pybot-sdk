"""Command based robot template."""
import commands2
import commands2.button
import constants
import wpilib


class RobotContainer:
    """Robot container for command based robot template."""

    def __init__(self) -> None:
        """Initialize the robot subsystems, autonomous command chooser, etc."""
        # Subsystems
        #self.drivetrain = Drivetrain()

        # Controllers
        self.driver = commands2.button.CommandXboxController(constants.CONTROLLER_PORT)

        # Auto chooser
        self.auto_chooser = wpilib.SendableChooser()
        self.auto_chooser.setDefaultOption("Do Nothing", commands2.cmd.none())
        wpilib.SmartDashboard.putData("Auto Chooser", self.auto_chooser)

        self.configure_bindings()

    def configure_bindings(self) -> None:
        """Bind the controller buttons to commands."""
        # Example of how to set a default command for a subsystem
        #self.drivetrain.setDefaultCommand(
        #    ArcadeDrive(
        #        self.drivetrain,
        #        lambda: -self.driver.getLeftY(),
        #        lambda: -self.driver.getRightX(),
        #    )

        # Example button binding:
        # self.driver.a().onTrue(SomeCommand(self.some_subsystem))
        pass

    def get_autonomous_command(self) -> commands2.Command:
        """Return the command to run in autonomous mode."""
        return self.auto_chooser.getSelected()