"""Tests for the packaged Limelight MagicBot component."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def _load_limelight_module(monkeypatch, values: dict[str, float]):
    """Load the component with small stand-ins for RobotPy's libraries."""
    entries = {}

    class FakeEntry:
        def __init__(self, name: str):
            self.name = name

        def getDouble(self, default: float) -> float:
            return values.get(self.name, default)

        def setDouble(self, value: float) -> None:
            values[self.name] = value

    class FakeTable:
        def getEntry(self, name: str) -> FakeEntry:
            entries[name] = FakeEntry(name)
            return entries[name]

    table = FakeTable()
    ntcore = ModuleType("ntcore")
    ntcore.NetworkTableInstance = SimpleNamespace(
        getDefault=lambda: SimpleNamespace(getTable=lambda name: table)
    )
    magicbot = ModuleType("magicbot")
    magicbot.feedback = lambda function: function
    monkeypatch.setitem(sys.modules, "ntcore", ntcore)
    monkeypatch.setitem(sys.modules, "magicbot", magicbot)

    component_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pybot_sdk"
        / "components"
        / "limelight.py"
    )
    spec = spec_from_file_location("limelight_template", component_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Limelight, entries


def test_limelight_reads_camera_values(monkeypatch) -> None:
    """Expose the latest target readings from the camera's NetworkTable."""
    values = {
        "tv": 1.0,
        "tx": -4.5,
        "ty": 2.0,
        "ta": 16.0,
        "tl": 25.0,
    }
    Limelight, _ = _load_limelight_module(monkeypatch, values)
    limelight = Limelight()
    limelight.setup()

    limelight.execute()

    assert limelight.has_target is True
    assert limelight.horizontal_offset_degrees == -4.5
    assert limelight.vertical_offset_degrees == 2.0
    assert limelight.target_area_percent == 16.0
    assert limelight.pipeline_latency_ms == 25.0


def test_limelight_uses_safe_defaults_when_camera_has_no_values(monkeypatch) -> None:
    """Treat missing NetworkTables values as no target and zero measurements."""
    Limelight, _ = _load_limelight_module(monkeypatch, {})
    limelight = Limelight()
    limelight.setup()

    limelight.execute()

    assert limelight.has_target is False
    assert limelight.horizontal_offset_degrees == 0.0
    assert limelight.vertical_offset_degrees == 0.0
    assert limelight.target_area_percent == 0.0
    assert limelight.pipeline_latency_ms == 0.0


def test_limelight_can_select_a_pipeline(monkeypatch) -> None:
    """Write a non-negative pipeline number to Limelight's NetworkTable."""
    values: dict[str, float] = {}
    Limelight, _ = _load_limelight_module(monkeypatch, values)
    limelight = Limelight()
    limelight.setup()

    limelight.set_pipeline(2)

    assert values["pipeline"] == 2


def test_limelight_rejects_negative_pipeline_numbers(monkeypatch) -> None:
    """Do not send invalid negative pipeline numbers to the camera."""
    Limelight, _ = _load_limelight_module(monkeypatch, {})
    limelight = Limelight()
    limelight.setup()

    with pytest.raises(ValueError, match="zero or greater"):
        limelight.set_pipeline(-1)
