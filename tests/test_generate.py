"""Deterministic hardware-data rendering and file-safety tests."""

import ast
from pathlib import Path

import pytest

from pybot_sdk.hardware.generate import render_hardware_module, write_hardware_module
from pybot_sdk.hardware.loader import load_hardware_map
from pybot_sdk.hardware.validate import validate_hardware_map


def test_generation_is_deterministic_python_data(tmp_path: Path) -> None:
    """Render repeatably and verify emitted literals without executing them."""
    source = Path("src/pybot_sdk/templates/magicbot/config/hardware.yml")
    document = load_hardware_map(source)
    assert validate_hardware_map(document) == []

    first = render_hardware_module(document)
    second = render_hardware_module(document)
    ast.parse(first)

    assert first == second
    assignments = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in ast.parse(first).body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    assert assignments["CONTROLLERS"]["driver"]["port"] == 0
    assert assignments["DEVICES"]["drive_right"]["inverted"] is True


def test_committed_template_data_matches_its_yaml() -> None:
    """Keep the committed template module in sync with its YAML source."""
    template = Path(__file__).parents[1] / "src/pybot_sdk/templates/magicbot"
    source = template / "config/hardware.yml"
    generated = template / "hardware_map.py"

    assert generated.read_text(encoding="utf-8") == render_hardware_module(
        load_hardware_map(source)
    )


def test_writer_refuses_unrelated_file_and_force_replaces_it(tmp_path: Path) -> None:
    """Require explicit force before replacing unrelated user content."""
    source = tmp_path / "hardware.yml"
    output = tmp_path / "hardware_map.py"
    source.write_text("schema_version: 1\n", encoding="utf-8")
    output.write_text("student code\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="pass --force"):
        write_hardware_module("generated\n", source, output)

    assert output.read_text(encoding="utf-8") == "student code\n"
    assert write_hardware_module("generated\n", source, output, force=True)
    assert output.read_text(encoding="utf-8") == "generated\n"


def test_writer_allows_idempotent_existing_output(tmp_path: Path) -> None:
    """Treat byte-identical output as a no-op rather than an overwrite."""
    source = tmp_path / "hardware.yml"
    output = tmp_path / "hardware_map.py"
    source.write_text("schema_version: 1\n", encoding="utf-8")
    output.write_text("generated\n", encoding="utf-8")

    assert not write_hardware_module("generated\n", source, output)


def test_writer_never_overwrites_source_even_with_force(tmp_path: Path) -> None:
    """Protect the authoritative YAML source even when force is requested."""
    source = tmp_path / "hardware.yml"
    source.write_text("schema_version: 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must not replace"):
        write_hardware_module("generated\n", source, source, force=True)
