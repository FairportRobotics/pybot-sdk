"""Scaffold and CLI integration tests."""

from pathlib import Path

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
