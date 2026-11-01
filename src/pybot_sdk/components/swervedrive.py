"""Coordinate four swerve modules and estimate the robot's field position.

The drive component turns normalized driver inputs into wheel speed and angle
targets. Each ``SwerveModule`` follows its own targets with PID control and
reports its own wheel telemetry. The drive reports robot-level pose feedback.

Declare the drive before its module annotations so MagicBot executes the drive
first each cycle, followed by its four modules. Configure each module by
setting the matching ``front_left_*``, ``front_right_*``, ``back_left_*``, or
``back_right_*`` values in ``createObjects``::

    import wpilib
    from components.gyro import Gyro
    from components.swervedrive import SwerveDrive
    from components.swervemodule import SwerveModule
    from magicbot import MagicRobot
    from wpimath.geometry import Translation2d

    class Robot(MagicRobot):
        gyro: Gyro
        drivetrain: SwerveDrive
        front_left: SwerveModule
        front_right: SwerveModule
        back_left: SwerveModule
        back_right: SwerveModule

        def createObjects(self):
            self.gyro_type = "adxrs450"

            # Each location is measured from the robot center, in meters.
            self.drivetrain_module_locations = (
                Translation2d(0.3, 0.3),    # front left
                Translation2d(0.3, -0.3),   # front right
                Translation2d(-0.3, 0.3),   # back left
                Translation2d(-0.3, -0.3),  # back right
            )
            self.drivetrain_max_speed_mps = 4.0
            self.drivetrain_max_angular_speed_rps = 6.0
            self.controller = wpilib.XboxController(0)

            # Configure each module's motors, encoders, and PID gains.
            # Encoder distances must be meters and steering angles degrees.
            self.front_left_drive_motor = wpilib.PWMSparkMax(0)
            self.front_left_steering_motor = wpilib.PWMSparkMax(1)
            self.front_left_drive_encoder = wpilib.Encoder(0, 1)
            self.front_left_steering_encoder = wpilib.Encoder(2, 3)
            self.front_left_drive_encoder.setDistancePerPulse(0.001)
            self.front_left_steering_encoder.setDistancePerPulse(360.0 / 2048)
            self.front_left_steering_offset_degrees = 0.0
            self.front_left_drive_pid = (0.2, 0.0, 0.0)
            self.front_left_steering_pid = (0.01, 0.0, 0.0)

            self.front_right_drive_motor = wpilib.PWMSparkMax(2)
            self.front_right_steering_motor = wpilib.PWMSparkMax(3)
            self.front_right_drive_encoder = wpilib.Encoder(4, 5)
            self.front_right_steering_encoder = wpilib.Encoder(6, 7)
            self.front_right_drive_encoder.setDistancePerPulse(0.001)
            self.front_right_steering_encoder.setDistancePerPulse(360.0 / 2048)
            self.front_right_steering_offset_degrees = 0.0
            self.front_right_drive_pid = (0.2, 0.0, 0.0)
            self.front_right_steering_pid = (0.01, 0.0, 0.0)

            self.back_left_drive_motor = wpilib.PWMSparkMax(4)
            self.back_left_steering_motor = wpilib.PWMSparkMax(5)
            self.back_left_drive_encoder = wpilib.Encoder(8, 9)
            self.back_left_steering_encoder = wpilib.Encoder(10, 11)
            self.back_left_drive_encoder.setDistancePerPulse(0.001)
            self.back_left_steering_encoder.setDistancePerPulse(360.0 / 2048)
            self.back_left_steering_offset_degrees = 0.0
            self.back_left_drive_pid = (0.2, 0.0, 0.0)
            self.back_left_steering_pid = (0.01, 0.0, 0.0)

            self.back_right_drive_motor = wpilib.PWMSparkMax(6)
            self.back_right_steering_motor = wpilib.PWMSparkMax(7)
            self.back_right_drive_encoder = wpilib.Encoder(12, 13)
            self.back_right_steering_encoder = wpilib.Encoder(14, 15)
            self.back_right_drive_encoder.setDistancePerPulse(0.001)
            self.back_right_steering_encoder.setDistancePerPulse(360.0 / 2048)
            self.back_right_steering_offset_degrees = 0.0
            self.back_right_drive_pid = (0.2, 0.0, 0.0)
            self.back_right_steering_pid = (0.01, 0.0, 0.0)

        def teleopPeriodic(self):
            self.drivetrain.drive(
                forward=-self.controller.getLeftY(),
                strafe=-self.controller.getLeftX(),
                turn=-self.controller.getRightX(),
                field_relative=True,
            )

Inputs to ``drive`` are joystick-style values from -1.0 to 1.0. Positive
forward means toward the front of the robot, positive strafe means left, and
positive turn means counterclockwise. Field-relative driving interprets the
forward and strafe directions using the field instead of the robot's current
orientation.

The hardware ports, encoder scale, steering offsets, and PID gains are examples,
not ready-to-use robot settings. Measure encoder scaling, check motor direction,
and tune with the wheels safely off the ground before driving. The example uses
the standard RobotPy 2026 four-module
``SwerveDrive4Kinematics`` and ``SwerveDrive4Odometry`` classes.
It shows 16 digital encoder channels as a wiring illustration; a standard
roboRIO has only 10 DIO ports, so use compatible CAN sensors or an appropriate
expansion device and follow the team's real wiring diagram.
"""

from __future__ import annotations

import wpilib
from magicbot import feedback
from wpimath import units as wpimath_units
from wpimath.geometry import Pose2d, Rotation2d, Translation2d
from wpimath.kinematics import (
    ChassisSpeeds,
    SwerveDrive4Kinematics,
    SwerveDrive4Odometry,
    SwerveModulePosition,
)

from .gyro import Gyro
from .swervemodule import SwerveModule


class SwerveDrive:
    """Drive a four-module swerve robot and track its pose."""

    front_left: SwerveModule
    front_right: SwerveModule
    back_left: SwerveModule
    back_right: SwerveModule
    gyro: Gyro
    module_locations: tuple[Translation2d, Translation2d, Translation2d, Translation2d]
    max_speed_mps: float
    max_angular_speed_rps: float

    def setup(self) -> None:
        """Validate configuration and initialize kinematics and odometry."""
        self._modules = (
            self.front_left,
            self.front_right,
            self.back_left,
            self.back_right,
        )
        if len(self.module_locations) != 4:
            raise ValueError("swervedrive_module_locations must contain four locations")
        if self.max_speed_mps <= 0:
            raise ValueError("swervedrive_max_speed_mps must be greater than zero")
        if self.max_angular_speed_rps <= 0:
            raise ValueError(
                "swervedrive_max_angular_speed_rps must be greater than zero"
            )
        if self.gyro is None:
            raise ValueError("swervedrive requires a gyro")

        self.kinematics = SwerveDrive4Kinematics(*self.module_locations)
        self.pose = Pose2d()
        self._is_simulation = wpilib.RobotBase.isSimulation()
        self._simulation_heading: Rotation2d | None = None
        self._odometry = SwerveDrive4Odometry(
            self.kinematics,
            self._get_heading(),
            self._get_module_positions(),
        )

        self.forward = 0.0
        self.strafe = 0.0
        self.turn = 0.0
        self.field_relative = False
        self._stop_requested = False

    def _get_heading(self) -> Rotation2d:
        """Return the latest gyro heading, or the simulation override."""
        if self._simulation_heading is not None:
            return self._simulation_heading
        return self.gyro.rotation

    def _get_module_positions(
        self,
    ) -> tuple[
        SwerveModulePosition,
        SwerveModulePosition,
        SwerveModulePosition,
        SwerveModulePosition,
    ]:
        """Read all wheel positions in the kinematics' configured order."""
        return (
            self.front_left.get_position(),
            self.front_right.get_position(),
            self.back_left.get_position(),
            self.back_right.get_position(),
        )

    def drive(
        self,
        forward: float,
        strafe: float,
        turn: float,
        field_relative: bool = False,
    ) -> None:
        """Set normalized driver requests for the next robot cycle."""
        self.forward = self._clamp_input(forward)
        self.strafe = self._clamp_input(strafe)
        self.turn = self._clamp_input(turn)
        self.field_relative = field_relative
        self._stop_requested = False

    @staticmethod
    def _clamp_input(value: float) -> float:
        """Keep one joystick request in the expected -1-to-1 range."""
        return max(-1.0, min(1.0, value))

    def execute(self) -> None:
        """Calculate wheel targets, then update odometry."""
        if self._stop_requested:
            for module in self._modules:
                module.stop()
            self.pose = self._odometry.update(
                self._get_heading(),
                self._get_module_positions(),
            )
            return

        chassis_speeds = ChassisSpeeds(
            self.forward * self.max_speed_mps,
            self.strafe * self.max_speed_mps,
            self.turn * self.max_angular_speed_rps,
        )
        if self.field_relative:
            chassis_speeds = ChassisSpeeds.fromFieldRelativeSpeeds(
                chassis_speeds.vx,
                chassis_speeds.vy,
                chassis_speeds.omega,
                self._get_heading(),
            )

        states = self.kinematics.toSwerveModuleStates(chassis_speeds)
        states = self.kinematics.desaturateWheelSpeeds(states, self.max_speed_mps)
        for module, state in zip(self._modules, states, strict=True):
            module.set_desired_state(state)

        self.pose = self._odometry.update(
            self._get_heading(),
            self._get_module_positions(),
        )

    def reset_odometry(self, pose: Pose2d = Pose2d()) -> None:
        """Set the estimated field position using current sensor readings."""
        self._odometry.resetPosition(
            self._get_heading(),
            self._get_module_positions(),
            pose,
        )
        self.pose = pose

    def get_pose(self, units: str = "meters") -> Pose2d:
        """Return the estimated pose, converting X and Y if requested."""
        return Pose2d(
            self._convert_distance(self.pose.X(), "meters", units),
            self._convert_distance(self.pose.Y(), "meters", units),
            self.pose.rotation(),
        )

    @staticmethod
    def _convert_distance(distance: float, from_units: str, to_units: str) -> float:
        """Convert a distance between meters, inches, or feet."""
        source = from_units.strip().lower()
        target = to_units.strip().lower()

        if source in ("m", "meter", "meters"):
            meters = distance
        elif source in ("in", "inch", "inches"):
            meters = wpimath_units.inchesToMeters(distance)
        elif source in ("ft", "foot", "feet"):
            meters = wpimath_units.feetToMeters(distance)
        else:
            raise ValueError(
                f"Unsupported distance unit {from_units!r}; use meters, inches, or feet"
            )

        if target in ("m", "meter", "meters"):
            return meters
        if target in ("in", "inch", "inches"):
            return wpimath_units.metersToInches(meters)
        if target in ("ft", "foot", "feet"):
            return wpimath_units.metersToFeet(meters)
        else:
            raise ValueError(
                f"Unsupported distance unit {to_units!r}; use meters, inches, or feet"
            )

    def stop(self) -> None:
        """Stop every wheel module and clear driver requests."""
        self.forward = 0.0
        self.strafe = 0.0
        self.turn = 0.0
        self._stop_requested = True
        for module in self._modules:
            module.stop()

    def set_simulation_readings(
        self,
        heading: Rotation2d,
        module_readings: tuple[
            tuple[float, float, Rotation2d],
            tuple[float, float, Rotation2d],
            tuple[float, float, Rotation2d],
            tuple[float, float, Rotation2d],
        ],
    ) -> None:
        """Provide simulated gyro and module sensors without simulating motors.

        Each module reading is ``(distance_meters, speed_meters_per_second,
        angle)`` in front-left, front-right, back-left, back-right order.

        Raises:
            RuntimeError: If called on a real robot.
            ValueError: If readings for anything other than four modules are given.

        """
        if not self._is_simulation:
            raise RuntimeError("Simulation readings require a simulated robot")
        if len(module_readings) != 4:
            raise ValueError("Simulation readings must include all four modules")
        self._simulation_heading = heading
        for module, reading in zip(self._modules, module_readings, strict=True):
            module.set_simulation_readings(*reading)

    @feedback
    def odometry_enabled(self) -> bool:
        """Show whether gyro and module sensors are configured for odometry."""
        return self._odometry is not None

    @feedback
    def pose_x_meters(self) -> float:
        """Show the robot's estimated X position in meters."""
        return self.pose.X()

    @feedback
    def pose_y_meters(self) -> float:
        """Show the robot's estimated Y position in meters."""
        return self.pose.Y()

    @feedback
    def heading_degrees(self) -> float:
        """Show the robot's estimated heading in degrees."""
        return self.pose.rotation().degrees()
