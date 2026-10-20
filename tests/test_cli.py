"""Scaffold and CLI integration tests."""

import ast
import sys
from importlib import resources
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from pybot_sdk.cli import main


def test_version_prints_project_version(capsys) -> None:
    """Show the version declared in pyproject.toml."""
    with (Path(__file__).resolve().parents[1] / "pyproject.toml").open("rb") as file:
        expected_version = tomllib.load(file)["project"]["version"]

    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == expected_version


def test_new_creates_runnable_magicbot_project(tmp_path: Path) -> None:
    """Generate all starter assets and exercise map validation and generation."""
    destination = tmp_path / "robot_project"

    assert main(["new", str(destination), "--template", "magicbot"]) == 0
    assert (destination / "robot.py").is_file()
    assert (destination / "constants.py").is_file()
    assert (destination / "autonomous" / "__init__.py").is_file()
    assert (destination / "components" / "__init__.py").is_file()
    assert (destination / ".github" / "workflows" / "robotpy.yml").is_file()


def test_new_supports_paths_with_spaces(tmp_path: Path) -> None:
    """Accept destination paths containing spaces."""
    destination = tmp_path / "new robot"

    assert main(["new", str(destination)]) == 0
    assert (destination / "robot.py").is_file()


def test_new_creates_xrp_project(tmp_path: Path) -> None:
    """Generate the XRP starter assets."""
    destination = tmp_path / "xrp_robot"

    assert main(["new", str(destination), "--template", "xrp"]) == 0
    assert (destination / "robot.py").is_file()
    assert (destination / "components" / "xrptankdrive.py").is_file()
    assert (destination / "autonomous" / "do_nothing.py").is_file()


def test_new_creates_single_file_sysid_project(tmp_path: Path, capsys) -> None:
    """Generate the single-file TimedRobot SysId template."""
    destination = tmp_path / "sysid_robot"

    assert main(["new", str(destination), "--template", "sysid"]) == 0
    assert {path.name for path in destination.iterdir()} == {
        "README.md",
        "requirements.txt",
        "robot.py",
    }

    robot_source = (destination / "robot.py").read_text()
    robot_tree = ast.parse(robot_source)
    robot_class = next(
        node
        for node in robot_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Robot"
    )
    assert any(
        isinstance(base, ast.Attribute)
        and isinstance(base.value, ast.Name)
        and base.value.id == "wpilib"
        and base.attr == "TimedRobot"
        for base in robot_class.bases
    )
    assert "SequentialCommandGroup" in robot_source
    assert "quasistatic(direction.kForward)" in robot_source
    assert "quasistatic(direction.kReverse)" in robot_source
    assert "dynamic(direction.kForward)" in robot_source
    assert "dynamic(direction.kReverse)" in robot_source
    assert 'setDefaultOption("Do Nothing"' in robot_source
    assert 'addOption("Run SysId"' in robot_source
    assert "def apply_voltage" in robot_source
    assert "def log_motor_data" in robot_source
    assert capsys.readouterr().out == (
        f"Created a SysId Robot project at {destination}\n"
    )


def test_add_component_copies_template_to_project_components(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Copy a component template into the current project's components directory."""
    project = tmp_path / "robot_project"
    components = project / "components"
    components.mkdir(parents=True)
    monkeypatch.chdir(project)

    assert main(["add", "component", "gyro"]) == 0
    assert (components / "gyro.py").read_bytes() == resources.files(
        "pybot_sdk"
    ).joinpath("templates", "components", "gyro.py").read_bytes()
    assert capsys.readouterr().out == "Added component gyro to components/\n"


def test_add_logger_component_copies_template_to_project_components(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Copy the logger component template into the project's components directory."""
    project = tmp_path / "robot_project"
    components = project / "components"
    components.mkdir(parents=True)
    monkeypatch.chdir(project)

    assert main(["add", "component", "logger"]) == 0
    assert (components / "logger.py").read_bytes() == resources.files(
        "pybot_sdk"
    ).joinpath("templates", "components", "logger.py").read_bytes()
    assert capsys.readouterr().out == "Added component logger to components/\n"


def test_add_tankdrive_component_copies_template_to_project_components(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Copy the Tankdrive component template into the project."""
    project = tmp_path / "robot_project"
    components = project / "components"
    components.mkdir(parents=True)
    monkeypatch.chdir(project)

    assert main(["add", "component", "tankdrive"]) == 0
    assert (components / "tankdrive.py").read_bytes() == resources.files(
        "pybot_sdk"
    ).joinpath("templates", "components", "tankdrive.py").read_bytes()
    assert capsys.readouterr().out == "Added component tankdrive to components/\n"


def _load_logger_module(
    monkeypatch, data_log_manager: SimpleNamespace, entry_calls: list | None = None
):
    """Load the template with a fake WPILib data logger."""
    wpilib = ModuleType("wpilib")
    wpilib.DataLogManager = data_log_manager
    monkeypatch.setitem(sys.modules, "wpilib", wpilib)

    if entry_calls is None:
        entry_calls = []

    class FakeLogEntry:
        def __init__(self, log, name):
            entry_calls.append(("create", type(self).__name__, log, name))
            self.name = name

        def append(self, value):
            entry_calls.append(("append", self.name, value))

    wpiutil = ModuleType("wpiutil")
    wpiutil.__path__ = []
    log_module = ModuleType("wpiutil.log")
    log_module.BooleanLogEntry = type("BooleanLogEntry", (FakeLogEntry,), {})
    log_module.DoubleLogEntry = type("DoubleLogEntry", (FakeLogEntry,), {})
    log_module.IntegerLogEntry = type("IntegerLogEntry", (FakeLogEntry,), {})
    log_module.StringLogEntry = type("StringLogEntry", (FakeLogEntry,), {})
    wpiutil.log = log_module
    monkeypatch.setitem(sys.modules, "wpiutil", wpiutil)
    monkeypatch.setitem(sys.modules, "wpiutil.log", log_module)

    logger_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pybot_sdk"
        / "templates"
        / "components"
        / "logger.py"
    )
    spec = spec_from_file_location("logger_template", logger_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_logger_starts_and_writes_messages_when_enabled(monkeypatch) -> None:
    """Start DataLogManager and write messages when enabled."""
    calls = []
    data_log_manager = SimpleNamespace(
        start=lambda: calls.append(("start",)),
        log=lambda message: calls.append(("log", message)),
        getLog=lambda: "fake-log",
    )
    logger = _load_logger_module(monkeypatch, data_log_manager).Logger()
    logger.enabled = True

    logger.setup()
    logger.log("Teleop started")

    assert calls == [("start",), ("log", "Teleop started")]


def test_logger_does_not_start_or_write_when_disabled(monkeypatch) -> None:
    """Skip DataLogManager calls when logging is disabled."""
    calls = []
    data_log_manager = SimpleNamespace(
        start=lambda: calls.append(("start",)),
        log=lambda message: calls.append(("log", message)),
    )
    logger = _load_logger_module(monkeypatch, data_log_manager).Logger()

    logger.setup()
    logger.log("Ignored")

    assert calls == []


def test_logger_appends_named_values_using_typed_entries(monkeypatch) -> None:
    """Log supported scalar values using entries of the matching WPILib type."""
    calls = []
    entry_calls = []
    data_log_manager = SimpleNamespace(
        start=lambda: calls.append(("start",)),
        log=lambda message: calls.append(("log", message)),
        getLog=lambda: "fake-log",
    )
    logger = _load_logger_module(monkeypatch, data_log_manager, entry_calls).Logger()
    logger.enabled = True

    logger.setup()
    logger.log("Drive/Speed", 2.5)
    logger.log("Drive/Enabled", True)
    logger.log("Drive/Count", 3)
    logger.log("Drive/Mode", "auto")
    logger.log("Drive/Speed", 1.5)

    assert entry_calls == [
        ("create", "DoubleLogEntry", "fake-log", "Drive/Speed"),
        ("append", "Drive/Speed", 2.5),
        ("create", "BooleanLogEntry", "fake-log", "Drive/Enabled"),
        ("append", "Drive/Enabled", True),
        ("create", "IntegerLogEntry", "fake-log", "Drive/Count"),
        ("append", "Drive/Count", 3),
        ("create", "StringLogEntry", "fake-log", "Drive/Mode"),
        ("append", "Drive/Mode", "auto"),
        ("append", "Drive/Speed", 1.5),
    ]


def test_logger_rejects_reusing_entry_name_with_another_type(monkeypatch) -> None:
    """Reject a value type change for a named entry."""
    data_log_manager = SimpleNamespace(
        start=lambda: None,
        log=lambda message: None,
        getLog=lambda: "fake-log",
    )
    logger = _load_logger_module(monkeypatch, data_log_manager).Logger()
    logger.enabled = True
    logger.setup()

    logger.log("Drive/Speed", 2.5)
    try:
        logger.log("Drive/Speed", "fast")
    except TypeError as error:
        assert "created with another type" in str(error)
    else:
        raise AssertionError("expected TypeError for a changed entry type")


def test_logger_rejects_unsupported_typed_value(monkeypatch) -> None:
    """Reject data types that WPILib typed entries do not support."""
    data_log_manager = SimpleNamespace(
        start=lambda: None,
        log=lambda message: None,
        getLog=lambda: "fake-log",
    )
    logger = _load_logger_module(monkeypatch, data_log_manager).Logger()
    logger.enabled = True
    logger.setup()

    try:
        logger.log("Drive/Value", [1, 2])
    except TypeError as error:
        assert "strings, booleans, integers, or floats" in str(error)
    else:
        raise AssertionError("expected TypeError for an unsupported value")


def test_add_component_reports_unknown_component(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Report a clear error when the requested component template is missing."""
    project = tmp_path / "robot_project"
    (project / "components").mkdir(parents=True)
    monkeypatch.chdir(project)

    assert main(["add", "component", "unknown"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "pybot: unknown component: unknown\n"
