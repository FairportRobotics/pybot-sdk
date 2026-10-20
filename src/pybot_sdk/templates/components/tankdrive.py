"""A tank-drive component for MagicBot.

Put the motors and any sensors you want to use in a dictionary. For example:

    import wpilib
    from components import XboxController
    from components.gyro import Gyro
    from components.tankdrive import Tankdrive
    from magicbot import MagicRobot

    class Robot(MagicRobot):
        gyro: Gyro
        drivetrain: Tankdrive
        controller: XboxController

        def createObjects(self) -> None:
            left_motors = wpilib.MotorControllerGroup(
                wpilib.PWMSparkMax(0), wpilib.PWMSparkMax(1)
            )
            right_motors = wpilib.MotorControllerGroup(
                wpilib.PWMSparkMax(2), wpilib.PWMSparkMax(3)
            )
            self.drivetrain_components = {
                "left_motor": left_motors,
                "right_motor": right_motors,
                "left_encoder": wpilib.Encoder(0, 1),
                "right_encoder": wpilib.Encoder(2, 3),
                "gyro": self.gyro,
            }
            self.drivetrain_track_width = 0.62
            self.drivetrain_units = "meters"
            self.drivetrain_drive_mode = "arcade"

        def teleopPeriodic(self) -> None:
            self.drivetrain.throttle = -self.controller.getLeftY()
            self.drivetrain.turn = self.controller.getRightX()

To read the robot's position in feet, call
``self.drivetrain.get_pose("feet")``. The default is meters.

The dictionary must include ``left_motor`` and ``right_motor``. You can use a
single motor or a group of motors on each side. Encoders and the gyro are
optional. The robot's position is tracked when both encoders and a gyro are
provided. Otherwise, ``pose`` stays at its starting position. The gyro should
be the ``Gyro`` component from ``gyro.py``.

Set ``track_width`` to the distance between the left and right wheels.
``units`` defaults to ``"meters"`` and tells Tankdrive which units you use for
the track width and encoder readings. Supported units are meters, inches, and
feet. The ``get_pose`` method can return the robot's position in any of these
units. Tankdrive stores its pose in meters, as WPILib expects.

Set ``drive_mode`` to ``"arcade"``, ``"cheesy"``, or ``"tank"``. Arcade and
Cheesy use ``throttle`` and ``turn``. Tank mode uses ``left`` and ``right``.
Cheesy mode also uses the ``quick_turn`` input. Set these inputs from your
robot code before Tankdrive runs.

In simulation, call
``set_simulation_readings(left_distance, right_distance, heading)`` if your
physics model supplies sensor values directly. Give distances in the units
you selected above.
"""

from __future__ import annotations

from typing import Any

import wpilib
import wpilib.drive
from magicbot import feedback
from wpimath import units as wpimath_units
from wpimath.geometry import Pose2d, Rotation2d
from wpimath.kinematics import DifferentialDriveKinematics, DifferentialDriveOdometry


class Tankdrive:
    """Drive a robot using arcade, Cheesy, or tank controls."""

    # MagicBot injects these from robot attributes named after the component.
    # For a component named "drivetrain", set drivetrain_components, etc.
    components: dict[str, Any]
    track_width: float
    units: str = "meters"
    drive_mode: str = "arcade"

    throttle: float = 0.0
    turn: float = 0.0
    left: float = 0.0
    right: float = 0.0
    quick_turn: bool = False

    def setup(self) -> None:
        """Set up motor control and position tracking."""
        if not isinstance(self.components, dict):
            raise ValueError("tankdrive_components must be a dictionary")

        try:
            left_motor = self.components["left_motor"]
            right_motor = self.components["right_motor"]
        except KeyError as error:
            raise ValueError(
                "tankdrive_components must contain 'left_motor' and 'right_motor'"
            ) from error

        self.drive = wpilib.drive.DifferentialDrive(left_motor, right_motor)
        self.is_simulation = wpilib.RobotBase.isSimulation()
        track_width = self._convert_to_internal_units(self.track_width)
        if track_width <= 0:
            raise ValueError("tankdrive_track_width must be greater than zero")
        self.kinematics = DifferentialDriveKinematics(track_width)
        self.pose = Pose2d()
        self.odometry: DifferentialDriveOdometry | None = None

        self._left_encoder = self.components.get("left_encoder")
        self._right_encoder = self.components.get("right_encoder")
        self._gyro = self.components.get("gyro")
        self._simulation_readings: tuple[float, float, Rotation2d] | None = None

        if (
            self._left_encoder is not None
            and self._right_encoder is not None
            and self._gyro is not None
        ):
            self.odometry = DifferentialDriveOdometry(
                self._get_heading(),
                self._get_left_distance(),
                self._get_right_distance(),
            )

    @staticmethod
    def _convert_distance(distance: float, from_units: str, to_units: str) -> float:
        """Convert a distance between meters, inches, or feet."""
        from_units = from_units.strip().lower()
        to_units = to_units.strip().lower()

        if from_units in ("m", "meter", "meters"):
            distance_in_meters = distance
        elif from_units in ("in", "inch", "inches"):
            distance_in_meters = wpimath_units.inchesToMeters(distance)
        elif from_units in ("ft", "foot", "feet"):
            distance_in_meters = wpimath_units.feetToMeters(distance)
        else:
            raise ValueError(
                f"Unsupported distance unit {from_units!r}; use meters, inches, or feet"
            )

        if to_units in ("m", "meter", "meters"):
            return distance_in_meters
        if to_units in ("in", "inch", "inches"):
            return wpimath_units.metersToInches(distance_in_meters)
        if to_units in ("ft", "foot", "feet"):
            return wpimath_units.metersToFeet(distance_in_meters)
        raise ValueError(
            f"Unsupported distance unit {to_units!r}; use meters, inches, or feet"
        )

    def _convert_to_internal_units(self, distance: float) -> float:
        """Convert one of the configured distances into WPILib's standard unit."""
        return self._convert_distance(distance, self.units, "meters")

    def _get_heading(self) -> Rotation2d:
        """Get the robot's heading from the gyro or simulation."""
        if self._simulation_readings is not None:
            return self._simulation_readings[2]
        if self._gyro is None:
            raise RuntimeError("Odometry requires a gyro")
        return self._gyro.rotation

    def _get_left_distance(self) -> float:
        """Get the left encoder distance in meters."""
        if self._simulation_readings is not None:
            return self._convert_to_internal_units(self._simulation_readings[0])
        if self._left_encoder is None:
            raise RuntimeError("Odometry requires a left encoder")
        return self._convert_to_internal_units(self._left_encoder.getDistance())

    def _get_right_distance(self) -> float:
        """Get the right encoder distance in meters."""
        if self._simulation_readings is not None:
            return self._convert_to_internal_units(self._simulation_readings[1])
        if self._right_encoder is None:
            raise RuntimeError("Odometry requires a right encoder")
        return self._convert_to_internal_units(self._right_encoder.getDistance())

    def execute(self) -> None:
        """Drive the robot and update its position if sensors are available."""
        mode = self.drive_mode.strip().lower()
        if mode == "arcade":
            self.drive.arcadeDrive(self.throttle, self.turn)
        elif mode == "cheesy":
            self.drive.curvatureDrive(self.throttle, self.turn, self.quick_turn)
        elif mode == "tank":
            self.drive.tankDrive(self.left, self.right)
        else:
            raise ValueError(
                f"Unknown tankdrive_drive_mode {self.drive_mode!r}; "
                "valid options: 'arcade', 'cheesy', or 'tank'"
            )

        if self.odometry is not None:
            self.pose = self.odometry.update(
                self._get_heading(),
                self._get_left_distance(),
                self._get_right_distance(),
            )

    def reset_odometry(self, pose: Pose2d = Pose2d()) -> None:
        """Reset the estimated pose to ``pose`` using the current sensors.

        Raises:
            RuntimeError: If encoders and a gyro were not all configured.

        """
        if self.odometry is None:
            raise RuntimeError("Odometry requires two encoders and a gyro")
        self.odometry.resetPosition(
            self._get_heading(),
            self._get_left_distance(),
            self._get_right_distance(),
            pose,
        )
        self.pose = pose

    def set_simulation_readings(
        self,
        left_distance: float,
        right_distance: float,
        heading: Rotation2d,
    ) -> None:
        """Set simulated sensor distances and heading for odometry.

        Distances use the configured ``units``. This method does not command
        the motors; a physics model remains responsible for motor simulation.

        Raises:
            RuntimeError: If called on a real robot or without odometry.

        """
        if not self.is_simulation:
            raise RuntimeError("Simulation readings require a simulated robot")
        if self.odometry is None:
            raise RuntimeError("Simulation readings require odometry sensors")
        self._simulation_readings = (left_distance, right_distance, heading)

    def reset_encoders(self) -> None:
        """Reset the configured encoders, if both are available."""
        if self._left_encoder is not None:
            self._left_encoder.reset()
        if self._right_encoder is not None:
            self._right_encoder.reset()

    def stop(self) -> None:
        """Stop both sides of the drivetrain."""
        self.drive.stopMotor()

    def get_pose(self, units: str = "meters") -> Pose2d:
        """Return the current robot position in the requested distance units.

        The stored ``pose`` always uses meters. This method returns a new pose
        with its X and Y coordinates converted to meters, inches, or feet.
        """
        return Pose2d(
            self._convert_distance(self.pose.X(), "meters", units),
            self._convert_distance(self.pose.Y(), "meters", units),
            self.pose.rotation(),
        )

    @feedback
    def odometry_enabled(self) -> bool:
        """Show whether pose estimation has all required sensors."""
        return self.odometry is not None

    @feedback
    def pose_x(self) -> float:
        """Show the estimated robot X coordinate in meters."""
        return self.pose.X()

    @feedback
    def pose_y(self) -> float:
        """Show the estimated robot Y coordinate in meters."""
        return self.pose.Y()

    @feedback
    def heading_degrees(self) -> float:
        """Show the estimated robot heading in degrees."""
        return self.pose.rotation().degrees()
