from pathlib import Path

from pybot_sdk.cli import main


def test_new_creates_runnable_magicbot_project(tmp_path: Path) -> None:
    destination = tmp_path / "robot_project"

    assert main(["new", str(destination), "--template", "magicbot"]) == 0
    assert (destination / "robot.py").is_file()
    assert (destination / "tests" / "test_drive.py").is_file()
    assert (destination / "config" / "hardware.yml").is_file()
    assert main(["hardware", "validate", str(destination / "config" / "hardware.yml")]) == 0
    generated_map = destination / "hardware_map.py"
    assert main(
        [
            "hardware",
            "generate",
            str(destination / "config" / "hardware.yml"),
            "--output",
            str(generated_map),
        ]
    ) == 0
    assert "CONTROLLERS" in generated_map.read_text(encoding="utf-8")
    for generated_file in destination.rglob("*"):
        if generated_file.is_file():
            assert "{{" not in generated_file.read_text(encoding="utf-8")


def test_new_supports_paths_with_spaces(tmp_path: Path) -> None:
    destination = tmp_path / "new robot"

    assert main(["new", str(destination)]) == 0
    assert (destination / "robot.py").is_file()


def test_new_refuses_nonempty_destination(tmp_path: Path, capsys) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    assert main(["new", str(destination)]) == 2
    assert marker.read_text(encoding="utf-8") == "keep"
    assert "not an empty directory" in capsys.readouterr().err


def test_generate_rejects_invalid_map_without_creating_output(
    tmp_path: Path, capsys
) -> None:
    hardware_map = tmp_path / "hardware.yml"
    generated = tmp_path / "hardware_map.py"
    hardware_map.write_text("schema_version: 99\n", encoding="utf-8")

    assert main(
        [
            "hardware",
            "generate",
            str(hardware_map),
            "--output",
            str(generated),
        ]
    ) == 1
    assert not generated.exists()
    assert "ERROR HWM002" in capsys.readouterr().err