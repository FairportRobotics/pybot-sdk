"""Command-line interface for pybot-sdk."""

import argparse
from importlib import resources
from pathlib import Path
import sys


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        create_project(args.project_directory, args.template)
    except (OSError, ValueError) as error:
        print(f"pybot: {error}", file=sys.stderr)
        return 2

    print(f"Created MagicBot project at {args.project_directory}")
    return 0