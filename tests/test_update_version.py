"""Tests for the date-based project version updater."""

from datetime import date
from pathlib import Path

import pytest

from scripts.update_version import update_version


def test_update_version_changes_only_project_version(tmp_path: Path) -> None:
    """Update the project's version without touching another version key."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "example"\nversion = "2026.10.21"\n\n'
        '[tool.example]\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    assert update_version(pyproject, date(2026, 10, 22))
    assert pyproject.read_text(encoding="utf-8") == (
        '[project]\nname = "example"\nversion = "2026.10.22"\n\n'
        '[tool.example]\nversion = "1.2.3"\n'
    )


def test_update_version_is_idempotent(tmp_path: Path) -> None:
    """Do not rewrite the file when its project version is already current."""
    pyproject = tmp_path / "pyproject.toml"
    contents = '[project]\nname = "example"\nversion = "2026.10.22"\n'
    pyproject.write_text(contents, encoding="utf-8")

    assert not update_version(pyproject, date(2026, 10, 22))
    assert pyproject.read_text(encoding="utf-8") == contents


def test_update_version_requires_project_version(tmp_path: Path) -> None:
    """Report malformed input instead of silently skipping the update."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "example"\n', encoding="utf-8")

    with pytest.raises(ValueError, match=r"\[project\].*version"):
        update_version(pyproject, date(2026, 10, 22))
