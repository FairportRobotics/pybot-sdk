from copy import deepcopy
from pathlib import Path

from pybot_sdk.cli import main
from pybot_sdk.hardware.loader import HardwareMapParseError, load_hardware_map
from pybot_sdk.hardware.validate import validate_hardware_map


VALID_MAP = {
    "schema_version": 1,
    "robot": {"name": "example_bot"},
    "can_buses": [{"name": "rio", "vendor_bus_name": ""}],
    "controllers": [{"name": "driver", "type": "xbox", "port": 0}],
    "devices": [
        {
            "name": "drive_left",
            "type": "talon_fx",
            "bus": "rio",
            "can_id": 1,
            "motor": "kraken",
            "subsystem": "drivetrain",
            "inverted": False,
        }
    ],
    "magicbot": {"components": [{"name": "drivetrain", "devices": ["drive_left"]}]},
}


def test_accepts_supported_falcon_and_kraken_identifiers() -> None:
    document = deepcopy(VALID_MAP)
    falcon = deepcopy(document["devices"][0])
    falcon.update(name="arm_motor", can_id=2, motor="falcon_500", subsystem="arm")
    document["devices"].append(falcon)
    document["magicbot"]["components"].append({"name": "arm", "devices": ["arm_motor"]})

    assert validate_hardware_map(document) == []


def test_rejects_unknown_fields_with_stable_structural_diagnostic() -> None:
    document = deepcopy(VALID_MAP)
    document["devices"][0]["canid"] = 4

    diagnostics = validate_hardware_map(document)

    assert diagnostics[0].code == "HWM100"
    assert diagnostics[0].path == "devices[0]"
    assert "unknown field" in diagnostics[0].message


def test_rejects_duplicate_can_ids_and_names_both_conflicting_entries() -> None:
    document = deepcopy(VALID_MAP)
    second = deepcopy(document["devices"][0])
    second.update(name="drive_right", inverted=True)
    document["devices"].append(second)

    diagnostics = validate_hardware_map(document)

    assert diagnostics[0].code == "HWM102"
    assert diagnostics[0].path == "devices[1].can_id"
    assert "devices[0].can_id" in diagnostics[0].message


def test_rejects_unresolved_bus_and_component_references() -> None:
    document = deepcopy(VALID_MAP)
    document["devices"][0]["bus"] = "canivore"
    document["devices"][0]["subsystem"] = "arm"
    document["magicbot"]["components"][0]["devices"] = ["missing_motor"]

    diagnostics = validate_hardware_map(document)

    assert {item.code for item in diagnostics} == {"HWM103", "HWM105", "HWM106"}


def test_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    hardware_map = tmp_path / "hardware.yml"
    hardware_map.write_text("schema_version: 1\nschema_version: 1\n", encoding="utf-8")

    try:
        load_hardware_map(hardware_map)
    except HardwareMapParseError as error:
        assert error.code == "HWM002"
        assert error.location == "line 2"
    else:
        raise AssertionError("duplicate YAML key was accepted")


def test_rejects_yaml_aliases_and_tags(tmp_path: Path) -> None:
    for source in ("name: &shared value\ncopy: *shared\n", "!!python/object/apply:os.system ['true']\n"):
        hardware_map = tmp_path / "hardware.yml"
        hardware_map.write_text(source, encoding="utf-8")

        try:
            load_hardware_map(hardware_map)
        except HardwareMapParseError as error:
            assert error.code == "HWM003"
        else:
            raise AssertionError("unsupported YAML feature was accepted")


def test_validate_cli_reports_invalid_map_and_exit_code(tmp_path: Path, capsys) -> None:
    hardware_map = tmp_path / "hardware.yml"
    hardware_map.write_text("schema_version: 99\n", encoding="utf-8")

    assert main(["hardware", "validate", str(hardware_map)]) == 1
    assert "ERROR HWM002" in capsys.readouterr().err