"""Tests for the packaged LED strip component."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_ledstrip_module(monkeypatch):
    """Load the component against a focused WPILib fake."""
    wpilib = ModuleType("wpilib")
    wpilib.Timer = SimpleNamespace(getFPGATimestamp=lambda: 0.0)
    monkeypatch.setitem(sys.modules, "wpilib", wpilib)

    component_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pybot_sdk"
        / "components"
        / "ledstrip.py"
    )
    spec = spec_from_file_location("ledstrip_component", component_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _execute(strip) -> list[tuple[int, int, int]]:
    """Capture and return the frame sent to the LED hardware."""
    frames = []
    strip.led_count = 3
    strip._hardware = SimpleNamespace(show=frames.append)
    strip.execute()
    return frames[0]


def test_ledstrip_uses_string_color_and_mode(monkeypatch) -> None:
    """Uppercase color and mode names are normalized before use."""
    module = _load_ledstrip_module(monkeypatch)
    strip = module.LedStrip()
    strip.color = "BLUE"
    strip.mode = "ON"

    assert strip.color == "blue"
    assert strip.mode == "on"
    assert _execute(strip) == [(0, 0, 255)] * 3


def test_ledstrip_uses_black_for_unsupported_color(monkeypatch) -> None:
    """An unknown color falls back to black."""
    module = _load_ledstrip_module(monkeypatch)
    strip = module.LedStrip()
    strip.color = "not-a-color"
    strip.mode = "on"

    assert _execute(strip) == [strip.COLORS["black"]] * 3


def test_ledstrip_uses_off_for_unsupported_mode(monkeypatch) -> None:
    """An unknown mode falls back to off."""
    module = _load_ledstrip_module(monkeypatch)
    strip = module.LedStrip()
    strip.color = "blue"
    strip.mode = "not-a-mode"

    assert _execute(strip) == [strip.COLORS["black"]] * 3
