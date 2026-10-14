"""XRP Tank drive component."""

import wpilib
import wpilib.drive
import wpimath.geometry
import wpimath.kinematics
import xrp


class XRPTankDrive:
    """Tank drive component for the XRP robot."""

    # Injected variables
    gyro: xrp.XRPGyro
    left_motor: xrp.XRPMotor
    right_motor: xrp.XRPMotor
    left_encoder: wpilib.Encoder
    right_encoder: wpilib.Encoder

    def setup(self) -> None:
        """Set up the tank drive component."""
        self.drive = wpilib.drive.DifferentialDrive(self.left_motor, self.right_motor)

        self.reset_gyro()

        self.reset_encoders()

        self.odometry = wpimath.kinematics.DifferentialDriveOdometry(
            wpimath.geometry.Rotation2d.fromDegrees(self.gyro.getAngle()),
            self.left_encoder.getDistance(),
            self.right_encoder.getDistance(),
        )

        self.pose = wpimath.geometry.Pose2d()
        self.throttle = 0.0
        self.rotation = 0.0

    def execute(self) -> None:
        """Run the component's periodic behavior."""
        self.go(self.throttle, self.rotation)
        self.update_pose()

    def go(self, throttle: float, rotation: float, square_inputs: bool = True) -> None:
        """Drive the robot using arcade drive."""
        self.drive.arcadeDrive(throttle, rotation, squareInputs=square_inputs)

    def reset_encoders(self) -> None:
        """Reset the left and right encoders."""
        self.left_encoder.reset()
        self.right_encoder.reset()

    def reset_gyro(self) -> None:
        """Reset the gyro."""
        self.gyro.reset()

    def stop(self) -> None:
        """Stop the robot."""
        self.drive.stopMotor()

    def update_pose(self) -> None:
        """Update the robot's pose using odometry."""
        self.pose = self.odometry.update(
            wpimath.geometry.Rotation2d.fromDegrees(self.gyro.getAngle()),
            self.left_encoder.getDistance(),
            self.right_encoder.getDistance(),
        )
