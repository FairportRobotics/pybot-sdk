"""XRP Tank drive component."""

import wpilib
import wpilib.drive
import wpimath.controller
import wpimath.geometry
import wpimath.kinematics
import xrp
import magicbot
from ntcore import NetworkTableInstance
from wpimath import units as wpimath_units


class XRPTankDrive:
    """Tank drive component for the XRP robot.

    Distance commands accept inches by default and convert to the meters used
    by the XRP template's encoders. Feet and meters are also supported.
    """

    # Injected variables
    distance_pid: tuple[float, float, float]
    heading_pid: tuple[float, float, float]
    gyro: xrp.XRPGyro
    left_motor: xrp.XRPMotor
    right_motor: xrp.XRPMotor
    left_encoder: wpilib.Encoder
    right_encoder: wpilib.Encoder

    def setup(self) -> None:
        """Set up the tank drive component."""
        self.target_heading: float | None = None
        self.target_distance: float | None = None
        self.drive = wpilib.drive.DifferentialDrive(self.left_motor, self.right_motor)
        self.heading_controller = wpimath.controller.PIDController(*self.heading_pid)
        self.distance_controller = wpimath.controller.PIDController(*self.distance_pid)
        self.distance_controller.setTolerance(0.01)
        self.heading_min = 0.0
        self.heading_max = 360.0
        self.heading_controller.enableContinuousInput(
            self.heading_min, self.heading_max
        )

        self.reset_gyro()

        self.reset_encoders()

        self.odometry = wpimath.kinematics.DifferentialDriveOdometry(
            wpimath.geometry.Rotation2d.fromDegrees(self.gyro.getAngle()),
            self.left_encoder.getDistance(),
            self.right_encoder.getDistance(),
        )

        self.field = wpilib.Field2d()
        wpilib.SmartDashboard.putData("Field", self.field)

        self.pose = wpimath.geometry.Pose2d()

        self.pose_publisher = (
            NetworkTableInstance.getDefault()
            .getStructTopic(
                "robot/pose",
                wpimath.geometry.Pose2d,
            )
            .publish()
        )

        self.throttle = 0.0
        self.rotation = 0.0

    def execute(self) -> None:
        """Run the component's periodic behavior."""
        rotation = self.rotation
        throttle = self.throttle
        if self.target_heading is not None:
            if not self.heading_min <= self.target_heading <= self.heading_max:
                raise ValueError(
                    f"target_heading outside {self.heading_min}-{self.heading_max}"
                )
            rotation = self.heading_controller.calculate(
                self.gyro.getAngle(), self.target_heading
            )

        if self.target_distance is not None:
            throttle = self.distance_controller.calculate(
                self.distance(), self.target_distance
            )
            if self.distance_controller.atSetpoint():
                throttle = 0.0
                self._cancel_distance_target()

        self.go(throttle, rotation)
        self.update_pose()

    # =========================================================================
    # ||                         Helper functions                            ||
    # =========================================================================

    def _cancel_distance_target(self) -> None:
        """Clear a distance command and its accumulated PID state."""
        self.target_distance = None
        self.distance_controller.reset()

    @magicbot.feedback
    def distance(self) -> float:
        """Get the current distance from the average of the left and right encoders."""
        return (self.left_encoder.getDistance() + self.right_encoder.getDistance()) / 2    

    @staticmethod
    def _distance_to_meters(distance: float, units: str) -> float:
        """Convert a distance in inches, feet, or meters to meters."""
        normalized_units = units.strip().lower()
        if normalized_units in ("in", "inch", "inches"):
            return wpimath_units.inchesToMeters(distance)
        if normalized_units in ("ft", "foot", "feet"):
            return wpimath_units.feetToMeters(distance)
        if normalized_units in ("m", "meter", "meters"):
            return distance
        raise ValueError(
            f"Unsupported distance unit {units!r}; use inches, feet, or meters"
        )

    def go(self, throttle: float, rotation: float, square_inputs: bool = True) -> None:
        """Drive the robot using arcade drive."""
        self.drive.arcadeDrive(throttle, rotation, squareInputs=square_inputs)
        
    def go_backward(self, distance: float, units: str = "inches") -> None:
        """Drive backward by a distance, in inches by default."""
        self.distance_controller.reset()
        converted_distance = self._distance_to_meters(distance, units)
        self.target_distance = self.distance() - converted_distance

    def go_forward(self, distance: float, units: str = "inches") -> None:
        """Drive forward by a distance, in inches by default."""
        self.distance_controller.reset()
        converted_distance = self._distance_to_meters(distance, units)
        self.target_distance = self.distance() + converted_distance

    @magicbot.feedback
    def left_encoder_count(self) -> float:
        """Get the left encoder count."""
        return self.left_encoder.get()

    def reset_encoders(self) -> None:
        """Reset the left and right encoders."""
        self._cancel_distance_target()
        self.left_encoder.reset()
        self.right_encoder.reset()

    def reset_gyro(self) -> None:
        """Reset the gyro."""
        self.gyro.reset()

    @magicbot.feedback
    def right_encoder_count(self) -> float:
        """Get the right encoder count."""
        return self.right_encoder.get()

    def stop(self) -> None:
        """Stop the robot."""
        self._cancel_distance_target()
        self.drive.stopMotor()

    def turn(self, degrees: float, ccw: bool = True) -> None:
        """Turn the robot by a specified number of degrees."""
        self.target_heading = self.gyro.getAngle() + (degrees if ccw else -degrees)

    def update_pose(self) -> None:
        """Update the robot's pose using odometry."""
        self.pose = self.odometry.update(
            wpimath.geometry.Rotation2d.fromDegrees(self.gyro.getAngle()),
            self.left_encoder.getDistance(),
            self.right_encoder.getDistance(),
        )
        self.field.setRobotPose(self.pose)
        self.pose_publisher.set(self.pose)

    @magicbot.feedback
    def velocity(self) -> float:
        """Get the average velocity of the left and right encoders."""
        return (self.left_encoder.getRate() + self.right_encoder.getRate()) / 2