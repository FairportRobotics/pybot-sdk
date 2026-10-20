"""Tests for the packaged Tankdrive MagicBot component."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from math import isclose
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_tankdrive_module(monkeypatch, simulation: bool = False):
    """Load the template against focused WPILib fakes."""
    calls = []

    class FakeRotation2d:
        def __init__(self, degrees: float = 0.0):
            self._degrees = degrees

        def degrees(self) -> float:
            return self._degrees

    class FakePose2d:
        def __init__(self, x: float = 0.0, y: float = 0.0, rotation=None):
            self._x = x
            self._y = y
            self._rotation = rotation or FakeRotation2d()

        def X(self) -> float:
            return self._x

        def Y(self) -> float:
            return self._y

        def rotation(self):
            return self._rotation

    class FakeDifferentialDrive:
        def __init__(self, left_motor, right_motor):
            calls.append(("init_drive", left_motor, right_motor))

        def arcadeDrive(self, throttle, turn):
            calls.append(("arcade", throttle, turn))

        def curvatureDrive(self, throttle, turn, quick_turn):
            calls.append(("curvature", throttle, turn, quick_turn))

        def tankDrive(self, left, right):
            calls.append(("tank", left, right))

        def stopMotor(self):
            calls.append(("stop",))

    class FakeDifferentialDriveKinematics:
        def __init__(self, track_width):
            calls.append(("kinematics", track_width))

    class FakeDifferentialDriveOdometry:
        def __init__(self, heading, left_distance, right_distance):
            calls.append(("init_odometry", heading, left_distance, right_distance))

        def update(self, heading, left_distance, right_distance):
            calls.append(("update_odometry", heading, left_distance, right_distance))
            return FakePose2d(left_distance, right_distance, heading)

        def resetPosition(self, heading, left_distance, right_distance, pose):
            calls.append(
                ("reset_odometry", heading, left_distance, right_distance, pose)
            )

    wpilib = ModuleType("wpilib")
    wpilib.__path__ = []
    wpilib.RobotBase = SimpleNamespace(isSimulation=lambda: simulation)
    drive_module = ModuleType("wpilib.drive")
    drive_module.DifferentialDrive = FakeDifferentialDrive
    wpilib.drive = drive_module

    magicbot = ModuleType("magicbot")
    magicbot.feedback = lambda function: function

    wpimath = ModuleType("wpimath")
    wpimath.__path__ = []
    geometry = ModuleType("wpimath.geometry")
    geometry.Pose2d = FakePose2d
    geometry.Rotation2d = FakeRotation2d
    kinematics = ModuleType("wpimath.kinematics")
    kinematics.DifferentialDriveKinematics = FakeDifferentialDriveKinematics
    kinematics.DifferentialDriveOdometry = FakeDifferentialDriveOdometry
    units = ModuleType("wpimath.units")
    units.inchesToMeters = lambda inches: inches * 0.0254
    units.feetToMeters = lambda feet: feet * 0.3048
    units.metersToInches = lambda meters: meters / 0.0254
    units.metersToFeet = lambda meters: meters / 0.3048

    monkeypatch.setitem(sys.modules, "wpilib", wpilib)
    monkeypatch.setitem(sys.modules, "wpilib.drive", drive_module)
    monkeypatch.setitem(sys.modules, "magicbot", magicbot)
    monkeypatch.setitem(sys.modules, "wpimath", wpimath)
    monkeypatch.setitem(sys.modules, "wpimath.geometry", geometry)
    monkeypatch.setitem(sys.modules, "wpimath.kinematics", kinematics)
    monkeypatch.setitem(sys.modules, "wpimath.units", units)
    wpimath.units = units

    template_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pybot_sdk"
        / "templates"
        / "components"
        / "tankdrive.py"
    )
    spec = spec_from_file_location("tankdrive_template", template_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, calls, FakePose2d, FakeRotation2d


class FakeEncoder:
    """Minimal encoder fake with a configurable distance."""

    def __init__(self, distance: float):
        """Store the current distance."""
        self.distance = distance
        self.reset_count = 0

    def getDistance(self) -> float:
        """Return the configured distance."""
        return self.distance

    def reset(self) -> None:
        """Count resets for test assertions."""
        self.reset_count += 1


class FakeGyro:
    """Minimal gyro fake with a fixed rotation."""

    def __init__(self, rotation):
        """Store the current rotation."""
        self.rotation = rotation


def _make_drivetrain(module, track_width=24.0, units="in", sensors=True):
    left_motor = object()
    right_motor = object()
    components = {
        "left_motor": left_motor,
        "right_motor": right_motor,
    }
    if sensors:
        components.update(
            left_encoder=FakeEncoder(12.0),
            right_encoder=FakeEncoder(24.0),
            gyro=FakeGyro(module.Rotation2d(30.0)),
        )
    drivetrain = module.Tankdrive()
    drivetrain.components = components
    drivetrain.track_width = track_width
    drivetrain.units = units
    return drivetrain, left_motor, right_motor


def test_setup_builds_kinematics_odometry_and_drives_each_mode(monkeypatch) -> None:
    """Use configured units for geometry and dispatch all control modes."""
    module, calls, _, _ = _load_tankdrive_module(monkeypatch)
    drivetrain, left_motor, right_motor = _make_drivetrain(module)
    drivetrain.setup()

    assert calls[0] == ("init_drive", left_motor, right_motor)
    assert calls[1][0] == "kinematics"
    assert isclose(calls[1][1], 0.6096)
    assert calls[2][0] == "init_odometry"
    assert calls[2][1] is drivetrain._gyro.rotation
    assert isclose(calls[2][2], 0.3048)
    assert isclose(calls[2][3], 0.6096)

    drivetrain.throttle = 0.5
    drivetrain.turn = -0.25
    drivetrain.quick_turn = True
    drivetrain.execute()
    drivetrain.drive_mode = "cheesy"
    drivetrain.execute()
    drivetrain.drive_mode = "tank"
    drivetrain.left = 0.2
    drivetrain.right = 0.4
    drivetrain.execute()

    assert [call for call in calls if call[0] in ("arcade", "curvature", "tank")] == [
        ("arcade", 0.5, -0.25),
        ("curvature", 0.5, -0.25, True),
        ("tank", 0.2, 0.4),
    ]
    assert isclose(drivetrain.pose.X(), 0.3048)
    assert isclose(drivetrain.pose.Y(), 0.6096)
    pose_in_inches = drivetrain.get_pose("inches")
    assert isclose(pose_in_inches.X(), 12.0)
    assert isclose(pose_in_inches.Y(), 24.0)
    assert isclose(drivetrain.get_pose("feet").X(), 1.0)


def test_missing_odometry_sensors_do_not_prevent_driving(monkeypatch) -> None:
    """Allow a motors-only configuration while keeping a pose attribute."""
    module, calls, _, _ = _load_tankdrive_module(monkeypatch)
    drivetrain, _, _ = _make_drivetrain(module, sensors=False)
    drivetrain.setup()
    drivetrain.execute()

    assert drivetrain.odometry is None
    assert drivetrain.pose.X() == 0.0
    assert ("arcade", 0.0, 0.0) in calls


def test_simulation_readings_update_odometry_in_configured_units(monkeypatch) -> None:
    """Allow a physics model to provide simulated sensor measurements."""
    module, calls, _, rotation_type = _load_tankdrive_module(
        monkeypatch, simulation=True
    )
    drivetrain, _, _ = _make_drivetrain(module)
    drivetrain.setup()
    heading = rotation_type(90.0)
    drivetrain.set_simulation_readings(36.0, 48.0, heading)
    drivetrain.execute()

    update = next(call for call in calls if call[0] == "update_odometry")
    assert update[1] is heading
    assert isclose(update[2], 0.9144)
    assert isclose(update[3], 1.2192)
    assert isclose(drivetrain.pose.X(), 0.9144)


def test_invalid_mode_and_missing_motors_raise_clear_errors(monkeypatch) -> None:
    """Reject incomplete motor configuration and unknown drive modes."""
    module, _, _, _ = _load_tankdrive_module(monkeypatch)
    drivetrain = module.Tankdrive()
    drivetrain.components = {"left_motor": object()}
    drivetrain.track_width = 0.6
    try:
        drivetrain.setup()
    except ValueError as error:
        assert "left_motor" in str(error) and "right_motor" in str(error)
    else:
        raise AssertionError("expected missing motor configuration to fail")

    drivetrain, _, _ = _make_drivetrain(module, sensors=False)
    drivetrain.setup()
    drivetrain.drive_mode = "unsupported"
    try:
        drivetrain.execute()
    except ValueError as error:
        assert "unsupported" in str(error)
    else:
        raise AssertionError("expected an unknown drive mode to fail")
