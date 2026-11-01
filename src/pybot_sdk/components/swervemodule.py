"""Control one drive wheel and steering wheel for a swerve drivetrain.

Each module owns the motors and encoders for one wheel. Drive distance and
speed use meters and meters per second. The steering encoder reports degrees;
``steering_offset_degrees`` corrects its zero so zero degrees means the wheel
points forward.

For example, configure one module in ``Robot.createObjects``::

    self.front_left_drive_motor = wpilib.PWMSparkMax(0)
    self.front_left_steering_motor = wpilib.PWMSparkMax(1)
    self.front_left_drive_encoder = wpilib.Encoder(0, 1)
    self.front_left_steering_encoder = wpilib.Encoder(2, 3)
    self.front_left_steering_offset_degrees = 0.0
    self.front_left_drive_pid = (0.2, 0.0, 0.0)
    self.front_left_steering_pid = (0.01, 0.0, 0.0)

The PID gains above are examples only. Tune them for the actual motors,
encoders, gearing, and robot. Each PID controller sends a motor output from
-1.0 to 1.0. Use only one closed-loop controller per motor.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import wpilib
import wpimath.controller
from magicbot import feedback
from wpimath.geometry import Rotation2d
from wpimath.kinematics import SwerveModulePosition, SwerveModuleState


@runtime_checkable
class MotorController(Protocol):
    """The small motor API required by a swerve module."""

    def set(self, output: float) -> None:
        """Set motor power from -1.0 to 1.0."""
        ...

    def stopMotor(self) -> None:
        """Stop the motor."""
        ...


@runtime_checkable
class DriveEncoder(Protocol):
    """The distance and speed readings needed from a drive encoder."""

    def getDistance(self) -> float:
        """Return wheel distance in meters."""
        ...

    def getRate(self) -> float:
        """Return wheel speed in meters per second."""
        ...


@runtime_checkable
class SteeringEncoder(Protocol):
    """The angle reading needed from a steering encoder."""

    def getDistance(self) -> float:
        """Return steering angle in degrees."""
        ...


class SwerveModule:
    """Measure and control one swerve wheel."""

    drive_motor: MotorController
    steering_motor: MotorController
    drive_encoder: DriveEncoder
    steering_encoder: SteeringEncoder
    steering_offset_degrees: float
    drive_pid: tuple[float, float, float]
    steering_pid: tuple[float, float, float]

    def setup(self) -> None:
        """Check configuration and create the wheel's two PID controllers."""
        for name in (
            "drive_motor",
            "steering_motor",
            "drive_encoder",
            "steering_encoder",
        ):
            if getattr(self, name, None) is None:
                raise ValueError(f"swerve module requires {name}")

        self._drive_controller = wpimath.controller.PIDController(*self.drive_pid)
        self._steering_controller = wpimath.controller.PIDController(*self.steering_pid)
        self._steering_controller.enableContinuousInput(-180.0, 180.0)
        self._desired_state = SwerveModuleState()
        self._is_simulation = wpilib.RobotBase.isSimulation()
        self._simulation_readings: tuple[float, float, Rotation2d] | None = None
        self._stopped = False

    def _current_angle(self) -> Rotation2d:
        """Return the calibrated wheel angle."""
        if self._simulation_readings is not None:
            return self._simulation_readings[2]
        return Rotation2d.fromDegrees(
            self.steering_encoder.getDistance() + self.steering_offset_degrees
        )

    def _drive_distance_meters(self) -> float:
        """Return how far the wheel has rolled."""
        if self._simulation_readings is not None:
            return self._simulation_readings[0]
        return self.drive_encoder.getDistance()

    def _drive_speed_meters_per_second(self) -> float:
        """Return how quickly the wheel is rolling."""
        if self._simulation_readings is not None:
            return self._simulation_readings[1]
        return self.drive_encoder.getRate()

    def set_desired_state(self, state: SwerveModuleState) -> None:
        """Set the wheel's requested speed and angle.

        WPILib may reverse the wheel's speed to reduce how far its steering
        motor must turn.
        """
        optimized_state = SwerveModuleState(state.speed, state.angle)
        optimized_state.optimize(self._current_angle())
        self._desired_state = optimized_state
        self._stopped = False

    def get_position(self) -> SwerveModulePosition:
        """Return wheel distance and steering angle for odometry."""
        return SwerveModulePosition(
            self._drive_distance_meters(),
            self._current_angle(),
        )

    def get_state(self) -> SwerveModuleState:
        """Return measured wheel speed and steering angle."""
        return SwerveModuleState(
            self._drive_speed_meters_per_second(),
            self._current_angle(),
        )

    def execute(self) -> None:
        """Run both PID loops once each robot cycle."""
        if self._stopped:
            return

        angle = self._current_angle()
        drive_output = self._drive_controller.calculate(
            self._drive_speed_meters_per_second(),
            self._desired_state.speed,
        )
        steering_output = self._steering_controller.calculate(
            angle.degrees(),
            self._desired_state.angle.degrees(),
        )
        self.drive_motor.set(self._clamp_motor_output(drive_output))
        self.steering_motor.set(self._clamp_motor_output(steering_output))

    @staticmethod
    def _clamp_motor_output(output: float) -> float:
        """Keep a PID output in the motor controller's accepted range."""
        return max(-1.0, min(1.0, output))

    def set_simulation_readings(
        self,
        distance_meters: float,
        speed_meters_per_second: float,
        angle: Rotation2d,
    ) -> None:
        """Set sensor readings supplied by a simulation physics model.

        This method does not simulate motors; the physics model remains
        responsible for calculating and supplying sensor values.

        Raises:
            RuntimeError: If called on a real robot.

        """
        if not self._is_simulation:
            raise RuntimeError("Simulation readings require a simulated robot")
        self._simulation_readings = (
            distance_meters,
            speed_meters_per_second,
            angle,
        )

    def stop(self) -> None:
        """Stop both motors until a new desired state is received."""
        self._desired_state = SwerveModuleState()
        self._drive_controller.reset()
        self._steering_controller.reset()
        self.drive_motor.stopMotor()
        self.steering_motor.stopMotor()
        self._stopped = True

    @feedback
    def measured_drive_distance_meters(self) -> float:
        """Show measured wheel distance in meters."""
        return self._drive_distance_meters()

    @feedback
    def measured_drive_speed_mps(self) -> float:
        """Show measured wheel speed in meters per second."""
        return self._drive_speed_meters_per_second()

    @feedback
    def measured_steering_angle_degrees(self) -> float:
        """Show the measured, calibrated steering angle in degrees."""
        return self._current_angle().degrees()

    @feedback
    def requested_drive_speed_mps(self) -> float:
        """Show the requested wheel speed in meters per second."""
        return self._desired_state.speed

    @feedback
    def requested_steering_angle_degrees(self) -> float:
        """Show the requested steering angle in degrees."""
        return self._desired_state.angle.degrees()

    @feedback
    def steering_error_degrees(self) -> float:
        """Show the shortest angle from the measured angle to its target."""
        error = self._desired_state.angle - self._current_angle()
        return error.degrees()
