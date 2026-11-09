"""Tests for the packaged MagicBot SwerveDrive and SwerveModule components."""

import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


class FakeRotation2d:
    """Small Rotation2d stand-in for tests that do not need RobotPy installed."""

    def __init__(self, degrees: float = 0.0):
        """Store an angle in degrees."""
        self._degrees = degrees

    @classmethod
    def fromDegrees(cls, degrees: float):
        """Construct an angle from degrees."""
        return cls(degrees)

    def degrees(self) -> float:
        """Return the normalized angle in degrees."""
        return (self._degrees + 180.0) % 360.0 - 180.0

    def __sub__(self, other):
        """Subtract another angle."""
        return FakeRotation2d(self.degrees() - other.degrees())


class FakePose2d:
    """Store X, Y, and heading like WPILib's Pose2d."""

    def __init__(self, x: float = 0.0, y: float = 0.0, rotation=None):
        """Store the pose coordinates."""
        self._x = x
        self._y = y
        self._rotation = rotation or FakeRotation2d()

    def X(self) -> float:
        """Return the X coordinate."""
        return self._x

    def Y(self) -> float:
        """Return the Y coordinate."""
        return self._y

    def rotation(self):
        """Return the heading."""
        return self._rotation


class FakeTranslation2d:
    """Store a module's position relative to the robot center."""

    def __init__(self, x: float, y: float):
        """Store the module coordinates."""
        self.x = x
        self.y = y


class FakeSwerveModuleState:
    """Minimal mutable wheel state with WPILib's optimization behavior."""

    def __init__(self, speed: float = 0.0, angle=None):
        """Store wheel speed and angle."""
        self.speed = speed
        self.angle = angle or FakeRotation2d()

    def optimize(self, current_angle):
        """Choose the equivalent target needing the least steering rotation."""
        error = (self.angle.degrees() - current_angle.degrees() + 180) % 360 - 180
        if abs(error) > 90:
            self.speed *= -1
            self.angle = FakeRotation2d(
                current_angle.degrees() + error - math.copysign(180, error)
            )


class FakeSwerveModulePosition:
    """Store encoder distance and wheel angle."""

    def __init__(self, distance: float = 0.0, angle=None):
        """Store encoder distance and wheel angle."""
        self.distance = distance
        self.angle = angle or FakeRotation2d()


class FakeChassisSpeeds:
    """Represent robot-relative velocity."""

    def __init__(self, vx: float, vy: float, omega: float):
        """Store chassis speeds."""
        self.vx = vx
        self.vy = vy
        self.omega = omega

    @classmethod
    def fromFieldRelativeSpeeds(cls, vx, vy, omega, robot_angle):
        """Convert field-relative velocity into the robot coordinate frame."""
        radians = math.radians(robot_angle.degrees())
        return cls(
            vx * math.cos(radians) + vy * math.sin(radians),
            -vx * math.sin(radians) + vy * math.cos(radians),
            omega,
        )


class FakePIDController:
    """P-only controller adequate for checking component setpoints and outputs."""

    def __init__(self, p: float, i: float, d: float):
        """Store the proportional gain."""
        self.p = p
        self.continuous = False

    def enableContinuousInput(self, minimum: float, maximum: float):
        """Enable shortest-path angle error."""
        self.continuous = True

    def calculate(self, measurement: float, setpoint: float) -> float:
        """Return a proportional response to the setpoint error."""
        error = setpoint - measurement
        if self.continuous:
            error = (error + 180.0) % 360.0 - 180.0
        return self.p * error

    def reset(self):
        """Reset the fake controller."""
        pass


class FakeSwerveDrive4Kinematics:
    """Calculate four wheel states in the configured front-left-first order."""

    def __init__(self, *locations):
        """Store all module locations."""
        self.locations = locations

    def toSwerveModuleStates(self, chassis_speeds):
        """Convert chassis velocity into four module targets."""
        return tuple(
            FakeSwerveModuleState(
                math.hypot(
                    chassis_speeds.vx - chassis_speeds.omega * location.y,
                    chassis_speeds.vy + chassis_speeds.omega * location.x,
                ),
                FakeRotation2d(
                    math.degrees(
                        math.atan2(
                            chassis_speeds.vy + chassis_speeds.omega * location.x,
                            chassis_speeds.vx - chassis_speeds.omega * location.y,
                        )
                    )
                ),
            )
            for location in self.locations
        )

    @staticmethod
    def desaturateWheelSpeeds(states, maximum_speed):
        """Scale all wheel speeds if any exceeds the configured maximum."""
        largest_speed = max(abs(state.speed) for state in states)
        if largest_speed > maximum_speed:
            scale = maximum_speed / largest_speed
            for state in states:
                state.speed *= scale
        return states


class FakeSwerveDrive4Odometry:
    """Record odometry sensor inputs and return a simple pose."""

    calls = []

    def __init__(self, kinematics, heading, positions):
        """Store the initial sensor readings."""
        self.positions = positions
        self.calls = [("init", heading, positions)]
        type(self).calls.append(self.calls[-1])

    def update(self, heading, positions):
        """Record new sensors and return a simple pose."""
        self.positions = positions
        self.calls.append(("update", heading, positions))
        type(self).calls.append(self.calls[-1])
        x = sum(position.distance for position in positions) / 4
        return FakePose2d(x, 0.0, heading)

    def resetPosition(self, heading, positions, pose):
        """Record the new odometry origin."""
        self.positions = positions
        self.calls.append(("reset", heading, positions, pose))
        type(self).calls.append(self.calls[-1])


class FakeEncoder:
    """Minimal encoder with configurable distance, speed, and reset behavior."""

    def __init__(self, distance: float = 0.0, rate: float = 0.0):
        """Set the distance and speed readings."""
        self.distance = distance
        self.rate = rate

    def getDistance(self) -> float:
        """Return the current distance."""
        return self.distance

    def getRate(self) -> float:
        """Return the current speed."""
        return self.rate


class FakeMotor:
    """Record motor outputs and stop calls."""

    def __init__(self):
        """Initialize the output record."""
        self.output = None
        self.stopped = False

    def set(self, output: float):
        """Record a motor output."""
        self.output = output
        self.stopped = False

    def stopMotor(self):
        """Record a motor stop."""
        self.output = 0.0
        self.stopped = True


class FakeGyro:
    """Provide the heading property expected from the SDK Gyro component."""

    def __init__(self, rotation=None):
        """Store the given heading or zero degrees."""
        self.rotation = rotation or FakeRotation2d()


def _load_components(monkeypatch, simulation: bool = True):
    """Load components against focused fakes so tests do not require RobotPy."""
    FakeSwerveDrive4Odometry.calls = []
    wpilib = ModuleType("wpilib")
    wpilib.RobotBase = SimpleNamespace(isSimulation=lambda: simulation)
    monkeypatch.setitem(sys.modules, "wpilib", wpilib)

    magicbot = ModuleType("magicbot")
    magicbot.feedback = lambda method: method
    magicbot.tunable = lambda value: value
    magicbot.will_reset_to = lambda value: value
    monkeypatch.setitem(sys.modules, "magicbot", magicbot)

    wpimath = ModuleType("wpimath")
    wpimath.__path__ = []
    controller = ModuleType("wpimath.controller")
    controller.PIDController = FakePIDController
    geometry = ModuleType("wpimath.geometry")
    geometry.Pose2d = FakePose2d
    geometry.Rotation2d = FakeRotation2d
    geometry.Translation2d = FakeTranslation2d
    wpimath.applyDeadband = lambda value, deadband: value
    kinematics = ModuleType("wpimath.kinematics")
    kinematics.ChassisSpeeds = FakeChassisSpeeds
    kinematics.SwerveDrive4Kinematics = FakeSwerveDrive4Kinematics
    kinematics.SwerveDrive4Odometry = FakeSwerveDrive4Odometry
    kinematics.SwerveModulePosition = FakeSwerveModulePosition
    kinematics.SwerveModuleState = FakeSwerveModuleState
    units = ModuleType("wpimath.units")
    units.inchesToMeters = lambda value: value * 0.0254
    units.feetToMeters = lambda value: value * 0.3048
    units.metersToInches = lambda value: value / 0.0254
    units.metersToFeet = lambda value: value / 0.3048
    wpimath.controller = controller
    wpimath.geometry = geometry
    wpimath.kinematics = kinematics
    wpimath.units = units
    for name, module in (
        ("wpimath", wpimath),
        ("wpimath.controller", controller),
        ("wpimath.geometry", geometry),
        ("wpimath.kinematics", kinematics),
        ("wpimath.units", units),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    package_name = "pybot_sdk.components"
    import pybot_sdk.components  # noqa: F401

    gyro = ModuleType(f"{package_name}.gyro")
    gyro.Gyro = FakeGyro
    monkeypatch.setitem(sys.modules, f"{package_name}.gyro", gyro)

    component_directory = (
        Path(__file__).resolve().parents[1] / "src" / "pybot_sdk" / "components"
    )

    def load(name: str):
        module_name = f"{package_name}.{name}"
        spec = importlib.util.spec_from_file_location(
            module_name, component_directory / f"{name}.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, module_name, module)
        spec.loader.exec_module(module)
        return module

    module_class = load("swervemodule").SwerveModule
    drive_class = load("swervedrive").SwerveDrive
    return module_class, drive_class


def _make_module(module_class, steering_angle=0.0, drive_rate=0.0):
    module = module_class()
    module.drive_motor = FakeMotor()
    module.steering_motor = FakeMotor()
    module.drive_encoder = FakeEncoder(distance=1.0, rate=drive_rate)
    module.steering_encoder = FakeEncoder(distance=steering_angle)
    module.steering_offset_degrees = 0.0
    module.drive_pid = (1.0, 0.0, 0.0)
    module.steering_pid = (0.01, 0.0, 0.0)
    module.setup()
    return module


def _make_drive(drive_class, modules, heading=None):
    drive = drive_class()
    (
        drive.front_left,
        drive.front_right,
        drive.back_left,
        drive.back_right,
    ) = modules
    drive.gyro = FakeGyro(heading)
    drive.module_locations = (
        FakeTranslation2d(0.3, 0.3),
        FakeTranslation2d(0.3, -0.3),
        FakeTranslation2d(-0.3, 0.3),
        FakeTranslation2d(-0.3, -0.3),
    )
    drive.max_speed_mps = 4.0
    drive.max_angular_speed_rps = 6.0
    drive.setup()
    return drive


def test_module_optimizes_angle_runs_pid_and_exposes_debug_feedback(monkeypatch):
    """Reverse wheel speed rather than steering more than 90 degrees."""
    module_class, _ = _load_components(monkeypatch)
    module = _make_module(module_class)

    module.set_desired_state(FakeSwerveModuleState(1.0, FakeRotation2d(170.0)))
    module.execute()

    assert module._desired_state.speed == -1.0
    assert module._desired_state.angle.degrees() == pytest.approx(-10.0)
    assert module.drive_motor.output == pytest.approx(-1.0)
    assert module.steering_motor.output == pytest.approx(-0.1)
    assert module.requested_drive_speed_mps() == pytest.approx(-1.0)
    assert module.measured_drive_distance_meters() == pytest.approx(1.0)
    assert module.steering_error_degrees() == pytest.approx(-10.0)


def test_module_clamps_pid_output_and_stop_is_persistent(monkeypatch):
    """Keep motor requests safe and do not restart after stop."""
    module_class, _ = _load_components(monkeypatch)
    module = _make_module(module_class)
    module.drive_pid = (10.0, 0.0, 0.0)
    module.setup()
    module.set_desired_state(FakeSwerveModuleState(1.0, FakeRotation2d()))
    module.execute()
    assert module.drive_motor.output == 1.0

    module.stop()
    module.execute()
    assert module.drive_motor.stopped
    assert module.steering_motor.stopped


def test_drive_calculates_four_states_updates_odometry_and_converts_pose(monkeypatch):
    """Run the four modules in order and update pose from their positions."""
    module_class, drive_class = _load_components(monkeypatch)
    modules = [_make_module(module_class) for _ in range(4)]
    for index, module in enumerate(modules, start=1):
        module.drive_encoder.distance = float(index)
    drive = _make_drive(drive_class, modules)

    drive.drive(forward=1.0, strafe=0.0, turn=0.0)
    drive.execute()

    assert [module._desired_state.speed for module in modules] == pytest.approx(
        [4.0, 4.0, 4.0, 4.0]
    )
    assert drive.pose.X() == pytest.approx(2.5)
    assert drive.get_pose("inches").X() == pytest.approx(2.5 / 0.0254)
    assert FakeSwerveDrive4Odometry.calls[-1][0] == "update"
    assert len(FakeSwerveDrive4Odometry.calls[-1][2]) == 4
    assert [
        position.distance for position in FakeSwerveDrive4Odometry.calls[-1][2]
    ] == [1.0, 2.0, 3.0, 4.0]
    with pytest.raises(ValueError, match="Unsupported distance unit"):
        drive.get_pose("yards")

    reset_pose = FakePose2d(2.0, 3.0, FakeRotation2d(45.0))
    drive.reset_odometry(reset_pose)
    assert drive.pose is reset_pose
    assert FakeSwerveDrive4Odometry.calls[-1][0] == "reset"


def test_drive_field_relative_speeds_desaturate_and_stop(monkeypatch):
    """Rotate field-relative requests and limit every wheel to max speed."""
    module_class, drive_class = _load_components(monkeypatch)
    modules = [_make_module(module_class) for _ in range(4)]
    drive = _make_drive(drive_class, modules, FakeRotation2d(90.0))
    drive.max_speed_mps = 1.0
    drive.drive(forward=1.0, strafe=0.0, turn=0.0, field_relative=True)
    drive.execute()

    assert [
        module._desired_state.angle.degrees() for module in modules
    ] == pytest.approx([-90.0, -90.0, -90.0, -90.0])
    assert all(abs(module._desired_state.speed) <= 1.0 for module in modules)

    drive.stop()
    assert all(module.drive_motor.stopped for module in modules)


def test_drive_turn_targets_preserve_module_order_after_desaturation(monkeypatch):
    """Keep wheel targets paired with their front-left-first module locations."""
    module_class, drive_class = _load_components(monkeypatch)
    modules = [_make_module(module_class) for _ in range(4)]
    drive = _make_drive(drive_class, modules)
    drive.max_speed_mps = 0.1
    drive.max_angular_speed_rps = 1.0
    drive.drive(forward=0.0, strafe=0.0, turn=1.0)
    drive.execute()

    assert [
        module._desired_state.angle.degrees() for module in modules
    ] == pytest.approx([-45.0, 45.0, 45.0, -45.0])
    assert [module._desired_state.speed for module in modules] == pytest.approx(
        [-0.1, 0.1, -0.1, 0.1]
    )


def test_smooth_swervedrive_uses_physical_robot_relative_speeds(monkeypatch):
    """Feed SmoothDriver speeds through the existing module/odometry pipeline."""
    module_class, _ = _load_components(monkeypatch)
    package_name = "pybot_sdk.components"
    tankdrive_module = ModuleType(f"{package_name}.tankdrive")
    tankdrive_module.Tankdrive = type("Tankdrive", (), {})
    monkeypatch.setitem(sys.modules, f"{package_name}.tankdrive", tankdrive_module)

    component_directory = (
        Path(__file__).resolve().parents[1] / "src" / "pybot_sdk" / "components"
    )
    module_name = f"{package_name}.smooth"
    spec = importlib.util.spec_from_file_location(
        module_name, component_directory / "smooth.py"
    )
    assert spec is not None and spec.loader is not None
    smooth_module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, smooth_module)
    spec.loader.exec_module(smooth_module)

    modules = [_make_module(module_class) for _ in range(4)]
    drive = _make_drive(smooth_module.SmoothSwerveDrive, modules)
    drive.smooth_driver = SimpleNamespace(
        speeds=FakeChassisSpeeds(1.0, 0.0, 0.0)
    )
    drive.execute()

    assert [module._desired_state.speed for module in modules] == pytest.approx(
        [1.0, 1.0, 1.0, 1.0]
    )
    assert [
        module._desired_state.angle.degrees() for module in modules
    ] == pytest.approx([0.0, 0.0, 0.0, 0.0])
    assert FakeSwerveDrive4Odometry.calls[-1][0] == "update"


def test_drive_rejects_bad_limits_and_simulation_is_explicit(monkeypatch):
    """Reject invalid configuration and limit simulated sensor writes."""
    module_class, drive_class = _load_components(monkeypatch, simulation=False)
    modules = [_make_module(module_class) for _ in range(4)]
    drive = _make_drive(drive_class, modules)
    with pytest.raises(RuntimeError, match="simulated robot"):
        drive.set_simulation_readings(
            FakeRotation2d(),
            tuple((0.0, 0.0, FakeRotation2d()) for _ in range(4)),
        )

    drive.max_speed_mps = 0.0
    with pytest.raises(ValueError, match="max_speed_mps"):
        drive.setup()


def test_drive_simulation_readings_feed_module_positions(monkeypatch):
    """Use externally supplied sensors for odometry in simulation."""
    module_class, drive_class = _load_components(monkeypatch, simulation=True)
    modules = [_make_module(module_class) for _ in range(4)]
    drive = _make_drive(drive_class, modules)
    readings = tuple(
        (float(index + 1), 0.0, FakeRotation2d(90.0)) for index in range(4)
    )
    drive.set_simulation_readings(FakeRotation2d(20.0), readings)
    drive.execute()

    assert drive.pose.X() == pytest.approx(2.5)
    assert drive.heading_degrees() == pytest.approx(20.0)
    assert [module.get_position().distance for module in modules] == [
        1.0,
        2.0,
        3.0,
        4.0,
    ]


def test_magicbot_injects_modules_and_runs_drive_before_module_control():
    """Verify MagicBot wiring and one-cycle motor updates when RobotPy is present."""
    hal = pytest.importorskip("hal")
    magicbot = pytest.importorskip("magicbot")
    wpimath_geometry = pytest.importorskip("wpimath.geometry")
    from pybot_sdk.components.gyro import Gyro
    from pybot_sdk.components.swervedrive import SwerveDrive
    from pybot_sdk.components.swervemodule import SwerveModule

    hal.initialize(500, 0)

    class Motor:
        """Minimal motor accepted by the module's runtime-checkable protocol."""

        def set(self, output: float) -> None:
            self.output = output

        def stopMotor(self) -> None:
            self.output = 0.0

    class Encoder:
        """Minimal encoder accepted by the module's runtime-checkable protocol."""

        def getDistance(self) -> float:
            return 0.0

        def getRate(self) -> float:
            return 0.0

    class Robot(magicbot.MagicRobot):
        gyro: Gyro
        drivetrain: SwerveDrive
        front_left: SwerveModule
        front_right: SwerveModule
        back_left: SwerveModule
        back_right: SwerveModule

    robot = Robot()
    robot._automodes = SimpleNamespace(modes={})
    robot.gyro_type = "adxrs450"
    robot.drivetrain_module_locations = (
        wpimath_geometry.Translation2d(0.3, 0.3),
        wpimath_geometry.Translation2d(0.3, -0.3),
        wpimath_geometry.Translation2d(-0.3, 0.3),
        wpimath_geometry.Translation2d(-0.3, -0.3),
    )
    robot.drivetrain_max_speed_mps = 4.0
    robot.drivetrain_max_angular_speed_rps = 6.0
    for module_name in ("front_left", "front_right", "back_left", "back_right"):
        setattr(robot, f"{module_name}_drive_motor", Motor())
        setattr(robot, f"{module_name}_steering_motor", Motor())
        setattr(robot, f"{module_name}_drive_encoder", Encoder())
        setattr(robot, f"{module_name}_steering_encoder", Encoder())
        setattr(robot, f"{module_name}_steering_offset_degrees", 0.0)
        setattr(robot, f"{module_name}_drive_pid", (0.2, 0.0, 0.0))
        setattr(robot, f"{module_name}_steering_pid", (0.01, 0.0, 0.0))

    robot._create_components()
    assert [name for name, _ in robot._components] == [
        "gyro",
        "drivetrain",
        "front_left",
        "front_right",
        "back_left",
        "back_right",
    ]

    robot.drivetrain.drive(0.5, 0.0, 0.0)
    for _, component in robot._components:
        component.execute()
    assert robot.front_left.drive_motor.output == pytest.approx(0.4)
