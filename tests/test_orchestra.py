"""Tests for the packaged CTRE Orchestra MagicBot component."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def _load_orchestra_module(monkeypatch, calls: list[tuple]):
    """Load the component with a small stand-in for Phoenix 6."""

    class FakeStatus:
        def __init__(self, ok: bool = True):
            self.ok = ok

        def is_ok(self) -> bool:
            return self.ok

        def __str__(self) -> str:
            return "fake error"

    class FakePlayer:
        def add_instrument(self, motor):
            calls.append(("add_instrument", motor))
            return FakeStatus()

        def load_music(self, music_file: str):
            calls.append(("load_music", music_file))
            return FakeStatus()

        def play(self):
            calls.append(("play",))
            return FakeStatus()

        def pause(self):
            calls.append(("pause",))
            return FakeStatus()

        def stop(self):
            calls.append(("stop",))
            return FakeStatus()

        def is_playing(self) -> bool:
            calls.append(("is_playing",))
            return True

    phoenix6 = ModuleType("phoenix6")
    phoenix6.orchestra = SimpleNamespace(Orchestra=FakePlayer)
    monkeypatch.setitem(sys.modules, "phoenix6", phoenix6)

    magicbot = ModuleType("magicbot")
    magicbot.feedback = lambda function: function
    monkeypatch.setitem(sys.modules, "magicbot", magicbot)

    component_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pybot_sdk"
        / "components"
        / "orchestra.py"
    )
    spec = spec_from_file_location("orchestra_template", component_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Orchestra


def test_orchestra_loads_song_and_controls_motor(monkeypatch) -> None:
    """Load a song onto the configured motor and expose playback controls."""
    calls: list[tuple] = []
    Orchestra = _load_orchestra_module(monkeypatch, calls)
    motor = object()
    orchestra = Orchestra()
    orchestra.motor = motor
    orchestra.music_file = "school_song.chrp"

    orchestra.setup()
    orchestra.play()
    orchestra.pause()
    orchestra.stop()

    assert orchestra.is_playing() is True
    assert calls == [
        ("add_instrument", motor),
        ("load_music", "school_song.chrp"),
        ("play",),
        ("pause",),
        ("stop",),
        ("is_playing",),
    ]


def test_orchestra_rejects_an_empty_song_path(monkeypatch) -> None:
    """Explain that MagicBot needs a music file to load."""
    calls: list[tuple] = []
    Orchestra = _load_orchestra_module(monkeypatch, calls)
    orchestra = Orchestra()
    orchestra.motor = object()
    orchestra.music_file = " "

    with pytest.raises(ValueError, match="orchestra_music_file"):
        orchestra.setup()

    assert calls == []


def test_orchestra_reports_phoenix_status_errors(monkeypatch) -> None:
    """Do not silently ignore a failed Phoenix Orchestra action."""
    calls: list[tuple] = []
    Orchestra = _load_orchestra_module(monkeypatch, calls)
    orchestra = Orchestra()

    class FailedStatus:
        def is_ok(self) -> bool:
            return False

        def __str__(self) -> str:
            return "fake error"

    with pytest.raises(RuntimeError, match="fake error"):
        orchestra._check_status(FailedStatus(), "load the song")
