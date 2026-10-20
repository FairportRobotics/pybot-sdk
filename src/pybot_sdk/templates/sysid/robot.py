"""Run WPILib SysId tests for one motor and its encoder."""

import commands2
import wpilib
from commands2.sysid import SysIdRoutine
from commands2.sysid.sysidroutine import SysIdRoutineLog

# Change these values to match the wiring on your robot.
MOTOR_PWM_PORT = 0
ENCODER_A_CHANNEL = 0
ENCODER_B_CHANNEL = 1

# Change this to the distance or angle measured for each encoder pulse.
ENCODER_DISTANCE_PER_PULSE = 1.0

# Lower these test settings if your mechanism needs less voltage or time.
SYSID_RAMP_RATE_VOLTS_PER_SECOND = 1.0
SYSID_STEP_VOLTAGE = 7.0
SYSID_TEST_TIMEOUT_SECONDS = 10.0


class Robot(wpilib.TimedRobot):
    """Robot program that runs SysId only when selected for autonomous."""

    def robotInit(self) -> None:
        """Create hardware, logging, and the autonomous chooser once at startup."""
        # This example uses a PWM motor controller and a quadrature encoder.
        # Replace these two objects if your mechanism uses different hardware.
        self.motor = wpilib.PWMSparkMax(MOTOR_PWM_PORT)
        self.encoder = wpilib.Encoder(ENCODER_A_CHANNEL, ENCODER_B_CHANNEL)
        self.encoder.setDistancePerPulse(ENCODER_DISTANCE_PER_PULSE)

        # WPILib's data log stores the SysId test states and motor measurements.
        wpilib.DataLogManager.start()

        # SysId commands need a subsystem so the command scheduler can reserve
        # this mechanism while a test is running.
        self.mechanism = commands2.Subsystem()
        self.sysid_routine = SysIdRoutine(
            SysIdRoutine.Config(
                rampRate=SYSID_RAMP_RATE_VOLTS_PER_SECOND,
                stepVoltage=SYSID_STEP_VOLTAGE,
                timeout=SYSID_TEST_TIMEOUT_SECONDS,
            ),
            SysIdRoutine.Mechanism(
                self.apply_voltage,
                self.log_motor_data,
                self.mechanism,
                name="mechanism",
            ),
        )

        # Keep the robot still by default. Select "Run SysId" on the dashboard
        # when you are ready to run these tests on a safe, clear practice field.
        self.autonomous_chooser = wpilib.SendableChooser()
        self.autonomous_chooser.setDefaultOption("Do Nothing", commands2.cmd.none())
        self.autonomous_chooser.addOption("Run SysId", self.make_sysid_command())
        wpilib.SmartDashboard.putData("Autonomous Mode", self.autonomous_chooser)

        self.autonomous_command: commands2.Command | None = None

    def robotPeriodic(self) -> None:
        """Update commands once each robot loop, as required by commands2."""
        commands2.CommandScheduler.getInstance().run()

    def apply_voltage(self, voltage: float) -> None:
        """Send SysId's requested voltage to the motor being tested."""
        self.motor.setVoltage(voltage)

    def log_motor_data(self, log: SysIdRoutineLog) -> None:
        """Record the motor's measured voltage, encoder position, and speed."""
        motor_log = log.motor("motor")

        # PWMSparkMax.get() is a percent output, so multiply by battery voltage
        # to record the motor's approximate applied voltage in volts.
        measured_voltage = self.motor.get() * wpilib.RobotController.getBatteryVoltage()
        motor_log.voltage(measured_voltage)
        motor_log.position(self.encoder.getDistance())
        motor_log.velocity(self.encoder.getRate())

    def make_sysid_command(self) -> commands2.Command:
        """Build the four tests in the order recommended for this template."""
        direction = SysIdRoutine.Direction
        return commands2.SequentialCommandGroup(
            self.sysid_routine.quasistatic(direction.kForward),
            self.sysid_routine.quasistatic(direction.kReverse),
            self.sysid_routine.dynamic(direction.kForward),
            self.sysid_routine.dynamic(direction.kReverse),
        )

    def autonomousInit(self) -> None:
        """Start the dashboard-selected autonomous command."""
        self.autonomous_command = self.autonomous_chooser.getSelected()
        if self.autonomous_command is not None:
            self.autonomous_command.schedule()

    def teleopInit(self) -> None:
        """Stop any autonomous test when the driver takes control."""
        self.stop_autonomous_command()

    def disabledInit(self) -> None:
        """Cancel commands and stop the motor whenever the robot is disabled."""
        self.stop_autonomous_command()
        self.motor.setVoltage(0.0)

    def testInit(self) -> None:
        """Stop the autonomous command before entering test mode."""
        self.stop_autonomous_command()
        self.motor.setVoltage(0.0)

    def stop_autonomous_command(self) -> None:
        """Cancel the selected autonomous command if one is running."""
        if self.autonomous_command is not None:
            self.autonomous_command.cancel()
            self.autonomous_command = None


if __name__ == "__main__":
    wpilib.run(Robot)
