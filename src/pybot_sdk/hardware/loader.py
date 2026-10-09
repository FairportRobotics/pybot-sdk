"""Strict YAML loading for team hardware maps."""

from pathlib import Path

import yaml
from yaml.constructor import ConstructorError
from yaml.tokens import AliasToken, AnchorToken, TagToken


class HardwareMapParseError(ValueError):
    def __init__(self, code: str, location: str, message: str):
        self.code = code
        self.location = location
        self.message = message
        super().__init__(message)


class _DuplicateKeyError(ConstructorError):
    pass


class _StrictSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "hardware-map keys must be strings",
                    key_node.start_mark,
                )
            if key in mapping:
                raise _DuplicateKeyError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_hardware_map(path: Path) -> object:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise HardwareMapParseError("HWM001", "$", str(error)) from error

    try:
        for token in yaml.scan(source, Loader=_StrictSafeLoader):
            if isinstance(token, (AliasToken, AnchorToken, TagToken)):
                line = token.start_mark.line + 1
                raise HardwareMapParseError(
                    "HWM003",
                    f"line {line}",
                    "YAML anchors, aliases, and tags are not supported",
                )
        return yaml.load(source, Loader=_StrictSafeLoader)
    except HardwareMapParseError:
        raise
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        location = f"line {mark.line + 1}" if mark is not None else "$"
        code = "HWM002" if isinstance(error, _DuplicateKeyError) else "HWM001"
        message = getattr(error, "problem", None) or str(error)
        raise HardwareMapParseError(code, location, message) from error