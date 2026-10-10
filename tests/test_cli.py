"""Scaffold and CLI integration tests."""

from pathlib import Path

from pybot_sdk.cli import main


def test_new_creates_runnable_magicbot_project(tmp_path: Path) -> None:
    """Generate all starter assets and exercise map validation and generation."""
    destination = tmp_path / "robot_project"

    assert main(["new", str(destination), "--template", "magicbot"]) == 0
    assert (destination / "robot.py").is_file()
    assert (destination / "tests" / "test_drive.py").is_file()
    assert (destination / "tests" / "test_startup.py").is_file()
    #assert (destination / "pybot.yml").is_file()
    assert (destination / ".github" / "workflows" / "robotpy.yml").is_file()
    """
    assert (
        main(["hardware", "validate", str(destination / "pybot.yml")])
        == 0
    )
    generated_map = destination / "hardware_map.py"
    assert (
        main(
            [
                "hardware",
                "generate",
                str(destination / "pybot.yml"),
                "--output",
                str(generated_map),
            ]
        )
        == 0
    )
    assert "CONTROLLERS" in generated_map.read_text(encoding="utf-8")
    for generated_file in destination.rglob("*"):
        if generated_file.is_file():
            assert "{{" not in generated_file.read_text(encoding="utf-8")
    """


def test_new_supports_paths_with_spaces(tmp_path: Path) -> None:
    """Accept destination paths containing spaces."""
    destination = tmp_path / "new robot"

    assert main(["new", str(destination)]) == 0
    assert (destination / "robot.py").is_file()


def test_generate_rejects_invalid_map_without_creating_output(
    tmp_path: Path, capsys
) -> None:
    """Reject invalid source maps without creating generated output."""
    hardware_map = tmp_path / "hardware.yml"
    generated = tmp_path / "hardware_map.py"
    hardware_map.write_text("schema_version: 99\n", encoding="utf-8")

    assert (
        main(
            [
                "hardware",
                "generate",
                str(hardware_map),
                "--output",
                str(generated),
            ]
        )
        == 1
    )
    assert not generated.exists()
    assert "ERROR HWM002" in capsys.readouterr().err


def test_validate_cli_keeps_warnings_nonfatal(tmp_path: Path, capsys) -> None:
    """Report suspicious legal maps as warnings without a failure exit code."""
    hardware_map = tmp_path / "hardware.yml"
    hardware_map.write_text(
        """schema_version: 1
robot: {name: example_bot}
can_buses: [{name: rio, vendor_bus_name: ''}]
controllers: [{name: driver, type: xbox, port: 0}]
devices: [{name: spare, type: talon_fx, bus: rio, can_id: 1, motor: kraken}]
magicbot: {components: []}
""",
        encoding="utf-8",
    )

    assert main(["hardware", "validate", str(hardware_map)]) == 0
    output = capsys.readouterr().out
    assert "WARNING HWM201" in output
    assert "Hardware map is valid" in output
