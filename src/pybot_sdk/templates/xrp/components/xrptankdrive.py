import xrp
import wpilib
import wpilib.drive
import wpimath.geometry
import wpimath.kinematics

class XRPTankDrive:
    gyro: xrp.XRPGyro
    left_motor: xrp.XRPMotor
    right_motor: xrp.XRPMotor
    left_encoder: wpilib.Encoder
    right_encoder: wpilib.Encoder

    def setup(self) -> None:
        self.drive = wpilib.drive.DifferentialDrive(
            self.left_motor, self.right_motor
        )

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
            wpimath.geometry.Rotation2d.fromDegrees(
                self.gyro.getAngle()
            ),
            self.left_encoder.getDistance(),
            self.right_encoder.getDistance(),
        )
