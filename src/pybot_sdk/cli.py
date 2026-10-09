"""Command-line interface for pybot-sdk."""

import argparse
from importlib import resources
from pathlib import Path
import sys

from pybot_sdk.hardware.generate import render_hardware_module, write_hardware_module
from pybot_sdk.hardware.loader import HardwareMapParseError, load_hardware_map
from pybot_sdk.hardware.validate import validate_hardware_map


def _copy_template(source, destination: Path) -> None:
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            target.mkdir()
            _copy_template(item, target)
        else:
            target.write_bytes(item.read_bytes())


def create_project(destination: Path, template_name: str) -> None:
    template = resources.files("pybot_sdk").joinpath("templates", template_name)
    if not template.is_dir():
        raise ValueError(f"unknown template: {template_name}")

    destination = destination.expanduser()
    if destination.is_symlink() or (
        destination.exists()
        and (not destination.is_dir() or any(destination.iterdir()))
    ):
        raise FileExistsError(f"destination is not an empty directory: {destination}")

    destination.mkdir(parents=True, exist_ok=True)
    _copy_template(template, destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pybot")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="create a RobotPy project")
    new.add_argument(
        "project_directory",
        nargs="?",
        default=Path("robot-project"),
        type=Path,
    )
    new.add_argument("--template", choices=("magicbot",), default="magicbot")
    hardware = commands.add_parser("hardware", help="inspect hardware maps")
    hardware_commands = hardware.add_subparsers(
        dest="hardware_command", required=True
    )
    validate = hardware_commands.add_parser("validate", help="validate a YAML map")
    validate.add_argument("path", nargs="?", type=Path, default=Path("config/hardware.yml"))
    generate = hardware_commands.add_parser(
        "generate", help="generate a Python hardware-data module"
    )
    generate.add_argument("path", nargs="?", type=Path, default=Path("config/hardware.yml"))
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "hardware":
        try:
            document = load_hardware_map(args.path)
        except HardwareMapParseError as error:
            print(
                f"ERROR {error.code} {error.location}: {error.message}",
                file=sys.stderr,
            )
            return 1

        diagnostics = validate_hardware_map(document)
        for diagnostic in diagnostics:
            stream = sys.stderr if diagnostic.severity == "error" else sys.stdout
            print(
                f"{diagnostic.severity.upper()} {diagnostic.code} "
                f"{diagnostic.path}: {diagnostic.message}",
                file=stream,
            )
        if any(diagnostic.severity == "error" for diagnostic in diagnostics):
            return 1
        if args.hardware_command == "generate":
            try:
                content = render_hardware_module(document)
                changed = write_hardware_module(
                    content, args.path, args.output, force=args.force
                )
            except (OSError, ValueError) as error:
                print(f"ERROR HWM200 {args.output}: {error}", file=sys.stderr)
                return 2
            result = "Generated" if changed else "Already up to date"
            print(f"{result}: {args.output}")
            return 0

        print(f"Hardware map is valid: {args.path}")
        return 0

    try:
        create_project(args.project_directory, args.template)
    except (OSError, ValueError) as error:
        print(f"pybot: {error}", file=sys.stderr)
        return 2

    print(f"Created MagicBot project at {args.project_directory}")
    return 0