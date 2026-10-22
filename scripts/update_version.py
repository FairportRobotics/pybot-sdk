"""Update the project version to today's date."""

import re
from datetime import date
from pathlib import Path

PROJECT_SECTION = re.compile(r"(?ms)^\[project\]\s*$.*?(?=^\[|\Z)")
VERSION_LINE = re.compile(r"""(?m)^(version\s*=\s*)(["'])([^"']+)\2(\s*(?:#.*)?)$""")


def update_version(pyproject_path: Path, current_date: date | None = None) -> bool:
    """Set [project].version to YYYY.MM.DD; return whether the file changed."""
    current_date = current_date or date.today()
    version = current_date.strftime("%Y.%m.%d")
    contents = pyproject_path.read_text(encoding="utf-8")
    sections = list(PROJECT_SECTION.finditer(contents))

    if len(sections) != 1:
        raise ValueError("pyproject.toml must contain exactly one [project] section")

    section = sections[0]
    project_text = section.group()
    version_lines = list(VERSION_LINE.finditer(project_text))
    if len(version_lines) != 1:
        raise ValueError("[project] must contain exactly one quoted version value")

    updated_project, replacements = VERSION_LINE.subn(
        rf"\g<1>\g<2>{version}\g<2>\g<4>", project_text, count=1
    )
    if replacements != 1:
        raise RuntimeError("Failed to update [project].version")
    if updated_project == project_text:
        return False

    updated_contents = (
        contents[: section.start()] + updated_project + contents[section.end() :]
    )
    pyproject_path.write_text(updated_contents, encoding="utf-8")
    return True


def main() -> None:
    """Update the repository's pyproject.toml version."""
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    today = date.today()
    changed = update_version(pyproject_path, today)
    if changed:
        print(f"Updated project version to {today:%Y.%m.%d}.")
    else:
        print(f"Project version is already current: {today:%Y.%m.%d}.")


if __name__ == "__main__":
    main()
