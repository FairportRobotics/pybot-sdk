"""Command-line interface for pybot-sdk."""

import argparse
import json
import shutil
import subprocess
import sys
from importlib import resources
from importlib.metadata import version as installed_version
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib import error, parse, request

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

TEMPLATE_NAMES = ("magicbot", "xrp", "command", "sysid")
LATEST_RELEASE_URL = (
    "https://api.github.com/repos/FairportRobotics/pybot-sdk/releases/latest"
)


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
        "components", f"{component_name}.py"
    )
    if not template.is_file():
        raise ValueError(f"unknown component: {component_name}")

    (destination / template.name).write_bytes(template.read_bytes())


def update_sdk() -> int:
    """Install the wheel attached to the latest GitHub release."""
    try:
        release_request = request.Request(
            LATEST_RELEASE_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "pybot-sdk",
            },
        )
        with request.urlopen(release_request, timeout=30) as response:
            release = json.load(response)

        if not isinstance(release, dict):
            raise ValueError("invalid GitHub release response")

        tag_name = release.get("tag_name")
        assets = release.get("assets")
        if not isinstance(tag_name, str) or not isinstance(assets, list):
            raise ValueError("invalid GitHub release response")

        wheel = next(
            (
                asset
                for asset in assets
                if isinstance(asset, dict)
                and isinstance(asset.get("name"), str)
                and asset["name"].startswith("pybot_sdk-")
                and asset["name"].endswith(".whl")
            ),
            None,
        )
        if wheel is None:
            raise ValueError("latest GitHub release does not include a pybot-sdk wheel")

        wheel_name = wheel["name"]
        download_url = wheel.get("browser_download_url")
        parsed_url = parse.urlparse(download_url or "")
        if (
            Path(wheel_name).name != wheel_name
            or parsed_url.scheme != "https"
            or parsed_url.netloc != "github.com"
        ):
            raise ValueError("invalid pybot-sdk wheel download URL")

        with TemporaryDirectory() as temporary_directory:
            wheel_path = Path(temporary_directory) / wheel_name
            download_request = request.Request(
                download_url, headers={"User-Agent": "pybot-sdk"}
            )
            with (
                request.urlopen(download_request, timeout=60) as response,
                wheel_path.open("wb") as wheel_file,
            ):
                shutil.copyfileobj(response, wheel_file)

            install = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--upgrade",
                    "--force-reinstall",
                    str(wheel_path),
                ],
                check=False,
            )
            if install.returncode != 0:
                print(
                    f"pybot: pip install failed with exit code {install.returncode}",
                    file=sys.stderr,
                )
                return install.returncode

        print(f"Updated pybot-sdk to {tag_name}.")
        return 0
    except (OSError, error.URLError, json.JSONDecodeError, ValueError) as exception:
        print(f"pybot: unable to update pybot-sdk: {exception}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for pybot commands."""
    parser = argparse.ArgumentParser(prog="pybot")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="show the pybot-sdk version")
    commands.add_parser("update", help="install the latest pybot-sdk release")
    new = commands.add_parser("new", help="create a RobotPy project")
    new.add_argument(
        "project_directory",
        nargs="?",
        default=Path("."),
        type=Path,
    )
    new.add_argument(
        "--template",
        choices=TEMPLATE_NAMES,
        default="magicbot",
    )
    add = commands.add_parser("add", help="add a component to the current project")
    add_commands = add.add_subparsers(dest="add_command", required=True)
    component = add_commands.add_parser("component", help="add a MagicBot component")
    component.add_argument("component_name")

    list_parser = commands.add_parser(
        "list", help="list available components or templates"
    )
    list_commands = list_parser.add_subparsers(dest="list_command", required=True)
    list_commands.add_parser("components", help="list addable components")
    list_commands.add_parser("templates", help="list project templates")

    return parser


def _list_components() -> list[str]:
    component_directory = resources.files("pybot_sdk").joinpath("components")
    return sorted(
        item.name.removesuffix(".py")
        for item in component_directory.iterdir()
        if item.is_file() and item.name.endswith(".py")
    )


def main(argv: list[str] | None = None) -> int:
    """Run a CLI command and return its process exit code."""
    args = build_parser().parse_args(argv)

    if args.command == "version":
        print(_project_version())
        return 0
    elif args.command == "update":
        return update_sdk()
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
            "sysid": "SysId Robot",
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
    elif args.command == "list":
        names = (
            _list_components()
            if args.list_command == "components"
            else sorted(TEMPLATE_NAMES)
        )
        print("\n".join(names))
        return 0
