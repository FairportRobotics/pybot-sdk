"""Command-line interface for pybot-sdk."""

import argparse
import sys
from importlib import resources
from pathlib import Path


def _copy_template(source, destination: Path) -> None:
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            target.mkdir()
            _copy_template(item, target)
        else:
            target.write_bytes(item.read_bytes())


def create_project(destination: Path, template_name: str) -> None:
    """Copy a packaged project template into an empty destination directory."""
    template = resources.files("pybot_sdk").joinpath("templates", template_name)
    if not template.is_dir():
        raise ValueError(f"unknown template: {template_name}")

    destination = destination.expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    _copy_template(template, destination)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for scaffold and hardware-map commands."""
    parser = argparse.ArgumentParser(prog="pybot")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="create a RobotPy project")
    new.add_argument(
        "project_directory",
        nargs="?",
        default=Path("."),
        type=Path,
    )
    new.add_argument("--template", choices=("magicbot", "xrp", "command"), default="magicbot")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a CLI command and return its process exit code."""
    args = build_parser().parse_args(argv)

    try:
        create_project(args.project_directory, args.template)
    except (OSError, ValueError) as error:
        print(f"pybot: {error}", file=sys.stderr)
        return 2

    template_label = {"magicbot": "MagicBot", "xrp": "XRP", "command": "Command Based Robot"}[args.template]
    print(f"Created {template_label} project at {args.project_directory}")
    return 0
