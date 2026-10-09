"""Structural and semantic validation for hardware maps."""

from dataclasses import dataclass
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str
    severity: str = "error"


def _path(parts) -> str:
    result = ""
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}" if result else str(part)
    return result or "$"


def _schema() -> dict[str, Any]:
    schema_text = (
        resources.files("pybot_sdk")
        .joinpath("hardware", "schema", "v1.json")
        .read_text(encoding="utf-8")
    )
    import json

    return json.loads(schema_text)


def _semantic_diagnostics(document: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    buses = {bus["name"] for bus in document["can_buses"]}
    components = {
        component["name"]: (index, component)
        for index, component in enumerate(document["magicbot"]["components"])
    }

    for collection_name, entries in (
        ("can_buses", document["can_buses"]),
        ("controllers", document["controllers"]),
        ("devices", document["devices"]),
        ("magicbot.components", document["magicbot"]["components"]),
    ):
        seen: dict[str, int] = {}
        for index, entry in enumerate(entries):
            name = entry["name"]
            if name in seen:
                diagnostics.append(
                    Diagnostic(
                        "HWM101",
                        f"{collection_name}[{index}].name",
                        f"duplicate name {name!r}; first declared at "
                        f"{collection_name}[{seen[name]}].name; use a unique name",
                    )
                )
            else:
                seen[name] = index

    ids_by_bus: dict[str, dict[int, int]] = {}
    device_indices: dict[str, int] = {}
    for index, device in enumerate(document["devices"]):
        device_name = device["name"]
        device_indices.setdefault(device_name, index)
        bus_name = device["bus"]
        if bus_name not in buses:
            diagnostics.append(
                Diagnostic(
                    "HWM103",
                    f"devices[{index}].bus",
                    f"CAN bus {bus_name!r} is not declared; add it to can_buses",
                )
            )
        else:
            ids = ids_by_bus.setdefault(bus_name, {})
            can_id = device["can_id"]
            if can_id in ids:
                diagnostics.append(
                    Diagnostic(
                        "HWM102",
                        f"devices[{index}].can_id",
                        f"CAN ID {can_id} on bus {bus_name!r} conflicts with "
                        f"devices[{ids[can_id]}].can_id; assign a unique ID on this bus",
                    )
                )
            else:
                ids[can_id] = index

        subsystem = device.get("subsystem")
        if subsystem is not None and subsystem not in components:
            diagnostics.append(
                Diagnostic(
                    "HWM105",
                    f"devices[{index}].subsystem",
                    f"MagicBot component {subsystem!r} is not declared; add it "
                    "to magicbot.components or correct the name",
                )
            )
        elif subsystem is not None:
            component_index, component = components[subsystem]
            if device_name not in component["devices"]:
                diagnostics.append(
                    Diagnostic(
                        "HWM108",
                        f"devices[{index}].subsystem",
                        f"device {device_name!r} declares {subsystem!r}, but is not "
                        f"listed in magicbot.components[{component_index}].devices; "
                        "make the ownership declarations agree",
                    )
                )

    ports: dict[int, int] = {}
    for index, controller in enumerate(document["controllers"]):
        port = controller["port"]
        if controller["type"] == "xbox" and port != 0:
            diagnostics.append(
                Diagnostic(
                    "HWM104",
                    f"controllers[{index}].port",
                    "the MVP Xbox controller must use USB port 0",
                )
            )
        if port in ports:
            diagnostics.append(
                Diagnostic(
                    "HWM104",
                    f"controllers[{index}].port",
                    f"USB port {port} conflicts with "
                    f"controllers[{ports[port]}].port; assign a unique port",
                )
            )
        else:
            ports[port] = index

    owners: dict[str, int] = {}
    for component_index, component in enumerate(document["magicbot"]["components"]):
        for device_position, device_name in enumerate(component["devices"]):
            path = f"magicbot.components[{component_index}].devices[{device_position}]"
            device_index = device_indices.get(device_name)
            if device_index is None:
                diagnostics.append(
                    Diagnostic(
                        "HWM106",
                        path,
                        f"device {device_name!r} is not declared; add it to devices",
                    )
                )
                continue
            if device_name in owners:
                diagnostics.append(
                    Diagnostic(
                        "HWM107",
                        path,
                        f"device {device_name!r} is already owned by "
                        f"magicbot.components[{owners[device_name]}]; each device "
                        "must have one component owner",
                    )
                )
            else:
                owners[device_name] = component_index
            declared_subsystem = document["devices"][device_index].get("subsystem")
            if declared_subsystem and declared_subsystem != component["name"]:
                diagnostics.append(
                    Diagnostic(
                        "HWM108",
                        path,
                        f"device {device_name!r} names subsystem "
                        f"{declared_subsystem!r}, not {component['name']!r}; make "
                        "the ownership declarations agree",
                    )
                )

    for index, device in enumerate(document["devices"]):
        if device["name"] not in owners and "subsystem" not in device:
            diagnostics.append(
                Diagnostic(
                    "HWM201",
                    f"devices[{index}].subsystem",
                    "device has no MagicBot component owner; add an explicit "
                    "subsystem assignment if it should be component-managed",
                    severity="warning",
                )
            )

    return diagnostics


def validate_hardware_map(document: object) -> list[Diagnostic]:
    validator = Draft202012Validator(_schema())
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        diagnostics = []
        for error in errors:
            path = _path(error.absolute_path)
            code = "HWM002" if path == "schema_version" else "HWM100"
            if error.validator == "additionalProperties":
                suggestion = "remove the unknown field or correct its spelling"
            elif error.validator == "required":
                suggestion = "add the missing required field"
            else:
                suggestion = "correct the value to match schema version 1"
            diagnostics.append(
                Diagnostic(code, path, f"{error.message}; {suggestion}")
            )
        return diagnostics

    return _semantic_diagnostics(document)