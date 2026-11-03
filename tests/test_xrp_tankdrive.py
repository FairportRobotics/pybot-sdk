"""Tests for the packaged XRP tank-drive component."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_tankdrive_module(monkeypatch):
    """Load the template against minimal RobotPy module stubs."""
    wpilib = ModuleType("wpilib")
    wpilib.__path__ = []
    wpilib.Encoder = type("Encoder", (), {})
    wpilib.Field2d = type("Field2d", (), {"setRobotPose": lambda self, pose: None})
    wpilib.SmartDashboard = SimpleNamespace(putData=lambda name, field: None)
    drive = ModuleType("wpilib.drive")
    drive.DifferentialDrive = type(
        "DifferentialDrive", (), {"__init__": lambda self, left, right: None}
    )
    wpilib.drive = drive

    wpimath = ModuleType("wpimath")
    wpimath.__path__ = []
    controller = ModuleType("wpimath.controller")
    controller.PIDController = FakePIDController
    wpimath.controller = controller
    geometry = ModuleType("wpimath.geometry")
    geometry.Rotation2d = type(
        "Rotation2d",
        (),
        {"fromDegrees": classmethod(lambda cls, degrees: degrees)},
    )
    geometry.Pose2d = type("Pose2d", (), {})
    wpimath.geometry = geometry
    kinematics = ModuleType("wpimath.kinematics")
    kinematics.DifferentialDriveOdometry = type(
        "DifferentialDriveOdometry",
        (),
        {
            "__init__": lambda self, heading, left_distance, right_distance: None,
            "update": lambda self, heading, left_distance, right_distance: object(),
        },
    )
    wpimath.kinematics = kinematics
    units = ModuleType("wpimath.units")
    units.inchesToMeters = lambda inches: inches * 0.0254
    units.feetToMeters = lambda feet: feet * 0.3048
    wpimath.units = units
    xrp = ModuleType("xrp")
    xrp.XRPGyro = type("XRPGyro", (), {})
    xrp.XRPMotor = type("XRPMotor", (), {})
    ntcore = ModuleType("ntcore")
    ntcore.NetworkTableInstance = type(
        "NetworkTableInstance",
        (),
        {
            "getDefault": staticmethod(
                lambda: SimpleNamespace(
                    getStructTopic=lambda name, data_type: SimpleNamespace(
                        publish=lambda: SimpleNamespace(set=lambda pose: None)
                    )
                )
            )
        },
    )

    modules = {
        "wpilib": wpilib,
        "wpilib.drive": drive,
        "wpimath": wpimath,
        "wpimath.controller": controller,
        "wpimath.geometry": geometry,
        "wpimath.kinematics": kinematics,
        "wpimath.units": units,
        "xrp": xrp,
        "ntcore": ntcore,
    }
    for name, module_stub in modules.items():
        monkeypatch.setitem(sys.modules, name, module_stub)

    template_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pybot_sdk"
        / "templates"
        / "xrp"
        / "components"
        / "xrptankdrive.py"
    )
    spec = spec_from_file_location("xrp_tankdrive_template", template_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakePIDController:
    """Capture heading-controller configuration and calculations."""

    def __init__(self, p: float, i: float, d: float):
        """Initialize the test controller."""
        self.gains = (p, i, d)
        self.continuous_input = None
        self.calculations = []
        self.tolerance = None
        self.is_at_setpoint = False
        self.reset_count = 0

    def enableContinuousInput(self, minimum: float, maximum: float) -> None:
        """Record the configured input range."""
        self.continuous_input = (minimum, maximum)

    def calculate(self, measurement: float, setpoint: float) -> float:
        """Record the input values and return a fixed output."""
        self.calculations.append((measurement, setpoint))
        return 0.4

    def setTolerance(self, tolerance: float) -> None:
        """Record the configured position tolerance."""
        self.tolerance = tolerance

    def atSetpoint(self) -> bool:
        """Return whether the simulated controller has reached its target."""
        return self.is_at_setpoint

    def reset(self) -> None:
        """Record a controller reset."""
        self.reset_count += 1


def _make_drivetrain(
    module, heading_pid=(0.02, 0.0, 0.0), distance_pid=(1.0, 0.0, 0.0)
):
    calls = []
    drivetrain = module.XRPTankDrive()
    drivetrain.heading_pid = heading_pid
    drivetrain.distance_pid = distance_pid
    drivetrain.left_motor = object()
    drivetrain.right_motor = object()
    drivetrain.gyro = SimpleNamespace(
        reset=lambda: None,
        getAngle=lambda: 350.0,
    )
    drivetrain.left_encoder = SimpleNamespace(
        reset=lambda: None,
        getDistance=lambda: 0.0,
    )
    drivetrain.right_encoder = SimpleNamespace(
        reset=lambda: None,
        getDistance=lambda: 0.0,
    )
    drivetrain.setup()
    drivetrain.drive = SimpleNamespace(
        arcadeDrive=lambda throttle, rotation, squareInputs: calls.append(
            (throttle, rotation, squareInputs)
        )
    )
    drivetrain.throttle = 0.6
    drivetrain.rotation = -0.2
    drivetrain.update_pose = lambda: None
    return drivetrain, calls


def test_execute_uses_manual_rotation_when_target_heading_is_unset(monkeypatch):
    """Keep regular arcade control when no heading target is selected."""
    module = _load_tankdrive_module(monkeypatch)
    heading_pid = (0.03, 0.001, 0.2)
    drivetrain, calls = _make_drivetrain(module, heading_pid)

    assert drivetrain.target_heading is None
    assert drivetrain.heading_controller.gains == heading_pid
    assert drivetrain.heading_controller.continuous_input == (0.0, 360.0)
    drivetrain.execute()

    assert calls == [(0.6, -0.2, True)]
    assert drivetrain.heading_controller.calculations == []


def test_execute_pid_controls_shortest_turn_to_target_heading(monkeypatch):
    """Use PID output in place of manual rotation for a selected heading."""
    module = _load_tankdrive_module(monkeypatch)
    drivetrain, calls = _make_drivetrain(module)
    drivetrain.target_heading = 10.0

    drivetrain.execute()

    assert drivetrain.heading_controller.calculations == [(350.0, 10.0)]
    assert calls == [(0.6, 0.4, True)]


def test_execute_rejects_target_heading_outside_range(monkeypatch):
    """Reject headings outside the supported 0-360 degree range."""
    module = _load_tankdrive_module(monkeypatch)
    drivetrain, _ = _make_drivetrain(module)
    drivetrain.target_heading = 361.0

    try:
        drivetrain.execute()
    except ValueError as error:
        assert "target_heading" in str(error)
    else:
        raise AssertionError("expected an out-of-range target_heading to fail")


def test_distance_commands_default_to_inches_and_support_explicit_units(monkeypatch):
    """Convert requested distances to meters relative to average encoder distance."""
    module = _load_tankdrive_module(monkeypatch)
    distance_pid = (0.8, 0.01, 0.02)
    drivetrain, calls = _make_drivetrain(module, distance_pid=distance_pid)
    drivetrain.left_encoder.getDistance = lambda: 1.0
    drivetrain.right_encoder.getDistance = lambda: 3.0

    drivetrain.go_forward(0.5, units="meters")
    assert drivetrain.target_distance == 2.5
    assert drivetrain.distance_controller.gains == distance_pid
    assert drivetrain.distance_controller.tolerance == 0.01

    drivetrain.execute()

    assert drivetrain.distance_controller.calculations == [(2.0, 2.5)]
    assert calls == [(0.4, -0.2, True)]

    drivetrain.go_backward(1.25, units="meters")
    assert drivetrain.target_distance == 0.75

    drivetrain.go_forward(10.0)
    assert drivetrain.target_distance == 2.254

    drivetrain.go_backward(1.0, units="feet")
    assert drivetrain.target_distance == 1.6952


def test_distance_commands_reject_unsupported_units(monkeypatch):
    """Raise a clear error for unknown distance units."""
    module = _load_tankdrive_module(monkeypatch)
    drivetrain, _ = _make_drivetrain(module)

    try:
        drivetrain.go_forward(1.0, units="yards")
    except ValueError as error:
        assert "Unsupported distance unit" in str(error)
    else:
        raise AssertionError("expected unsupported distance units to fail")


def test_distance_command_clears_when_at_setpoint(monkeypatch):
    """Return control to the manual throttle after reaching the target."""
    module = _load_tankdrive_module(monkeypatch)
    drivetrain, calls = _make_drivetrain(module)
    drivetrain.go_forward(1.0)
    drivetrain.distance_controller.is_at_setpoint = True

    drivetrain.execute()

    assert drivetrain.target_distance is None
    assert calls == [(0.0, -0.2, True)]

    drivetrain.distance_controller.is_at_setpoint = False
    drivetrain.execute()
    assert calls[-1] == (0.6, -0.2, True)


def test_stop_cancels_distance_command(monkeypatch):
    """Do not resume PID-controlled motion after stop is called."""
    module = _load_tankdrive_module(monkeypatch)
    drivetrain, calls = _make_drivetrain(module)
    stop_calls = []
    drivetrain.drive.stopMotor = lambda: stop_calls.append("stop")
    drivetrain.go_forward(1.0)

    drivetrain.stop()
    drivetrain.execute()

    assert drivetrain.target_distance is None
    assert stop_calls == ["stop"]
    assert calls == [(0.6, -0.2, True)]


def test_reset_encoders_cancels_distance_command(monkeypatch):
    """Avoid retaining a target based on encoder readings that were reset."""
    module = _load_tankdrive_module(monkeypatch)
    drivetrain, _ = _make_drivetrain(module)
    drivetrain.go_forward(1.0)

    drivetrain.reset_encoders()

    assert drivetrain.target_distance is None


def test_xrp_template_configures_distance_pid_gains():
    """Provide default distance PID gains to the generated robot."""
    constants_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pybot_sdk"
        / "templates"
        / "xrp"
        / "constants.py"
    )
    spec = spec_from_file_location("xrp_template_constants", constants_path)
    assert spec is not None
    assert spec.loader is not None
    constants = module_from_spec(spec)
    spec.loader.exec_module(constants)

    assert constants.Robot.DISTANCE_PID == (1.0, 0.0, 0.0)
