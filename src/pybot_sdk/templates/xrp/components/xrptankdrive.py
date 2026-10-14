import xrp
import wpilib
import wpilib.drive
import wpimath.geometry
import wpimath.kinematics
from magicbot import feedback

class XRPTankDrive:
    gyro: xrp.XRPGyro
    left_motor: xrp.XRPMotor
    right_motor: xrp.XRPMotor
    left_encoder: wpilib.Encoder
    right_encoder: wpilib.Encoder

    def setup(self) -> None:
        self.drive = wpilib.drive.DifferentialDrive(self.left_motor, self.right_motor)
        self.pose = wpimath.geometry.Pose2d(0, 0, wpimath.geometry.Rotation2d(0))
        self.reset_encoders()
        self.angle = self.gyro.getAngle() 
        self.odometry = wpimath.kinematics.DifferentialDriveOdometry(
            wpimath.geometry.Rotation2d(self.angle),
            self.left_encoder.getDistance(),
            self.right_encoder.getDistance(),
        )
        self.throttle = 0.0
        self.rotation = 0.0

    def execute(self) -> None:
        self.go(self.throttle, self.rotation)
        self.update_pose()

    def go(self, throttle: float, rotation: float, square_inputs: bool = True) -> None:
        self.drive.arcadeDrive(throttle, rotation, squareInputs=square_inputs)

    def reset_encoders(self) -> None:
        self.left_encoder.reset()
        self.right_encoder.reset()

    def reset_gyro(self) -> None:
        self.gyro.reset()

    def stop(self) -> None:
        self.drive.stopMotor()

    def update_pose(self) -> None:
        self.pose = self.odometry.update(
            wpimath.geometry.Rotation2d(self.gyro.getAngle()),
            self.left_encoder.getDistance(),
            self.right_encoder.getDistance(),
        )

    @feedback
    def pose(self) -> list:
        return [
            self.pose.X(),
            self.pose.Y(),
            self.pose.rotation().degrees(),
        ]