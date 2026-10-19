"""Command-line interface for pybot-sdk."""

import argparse
import sys
from importlib import resources
from importlib.metadata import version as installed_version
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def _copy_template(source, destination: Path) -> None:
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            target.mkdir()
            _copy_template(item, target)
        else:
            target.write_bytes(item.read_bytes())


def _project_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as file:
            return tomllib.load(file)["project"]["version"]
    return installed_version("pybot-sdk")


def create_project(destination: Path, template_name: str) -> None:
    """Copy a packaged project template into an empty destination directory."""
    template = resources.files("pybot_sdk").joinpath("templates", template_name)
    if not template.is_dir():
        raise ValueError(f"unknown template: {template_name}")

    destination = destination.expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    _copy_template(template, destination)


def add_component(component_name: str, destination: Path) -> None:
    """Copy a packaged component template into a project's components directory."""
    if Path(component_name).name != component_name or not component_name.isidentifier():
        raise ValueError(f"unknown component: {component_name}")

    template = resources.files("pybot_sdk").joinpath(
        "templates", "components", f"{component_name}.py"
    )
    if not template.is_file():
        raise ValueError(f"unknown component: {component_name}")

    (destination / template.name).write_bytes(template.read_bytes())


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for pybot commands."""
    parser = argparse.ArgumentParser(prog="pybot")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="show the pybot-sdk version")
    new = commands.add_parser("new", help="create a RobotPy project")
    new.add_argument(
        "project_directory",
        nargs="?",
        default=Path("."),
        type=Path,
    )
    new.add_argument(
        "--template", choices=("magicbot", "xrp", "command"), default="magicbot"
    )
    add = commands.add_parser("add", help="add a component to the current project")
    add_commands = add.add_subparsers(dest="add_command", required=True)
    component = add_commands.add_parser("component", help="add a MagicBot component")
    component.add_argument("component_name")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a CLI command and return its process exit code."""
    args = build_parser().parse_args(argv)

    if args.command == "version":
        print(_project_version())
        return 0
    elif args.command == "new":
        try:
            create_project(args.project_directory, args.template)
        except (OSError, ValueError) as error:
            print(f"pybot: {error}", file=sys.stderr)
            return 2

        labels = {
            "magicbot": "MagicBot",
            "xrp": "XRP",
            "command": "Command Based Robot",
        }
        print(f"Created a {labels[args.template]} project at {args.project_directory}")
        return 0
    elif args.command == "add" and args.add_command == "component":
        try:
            add_component(args.component_name, Path("components"))
        except (OSError, ValueError) as error:
            print(f"pybot: {error}", file=sys.stderr)
            return 2

        print(f"Added component {args.component_name} to components/")
        return 0
