"""Log event messages and named values to WPILib's managed data log.

In a RobotPy MagicBot project, declare the component and enable it in
``createObjects``::

    from components.logger import Logger
    from magicbot import MagicRobot

    class Robot(MagicRobot):
        logger: Logger

        def createObjects(self) -> None:
            self.logger_enabled = True

        def teleopInit(self) -> None:
            self.logger.log("Teleop started")

        def teleopPeriodic(self) -> None:
            self.logger.log("Drive/Speed", 2.5)
            self.logger.log("Drive/Enabled", True)

A single string argument is written to the DataLogManager's ``messages``
entry and printed to standard output. Pass a name and a string, boolean,
integer, or floating-point value to create a named typed entry in the data
log. Named entries retain their type, so using the same name with a different
type raises ``TypeError``. WPILib saves the ``.wpilog`` file to a connected
USB drive's ``logs`` directory, or to ``/home/lvuser/logs`` otherwise. The
component is disabled by default; when disabled, calls to ``log`` are ignored.
"""

from typing import overload

import wpilib
from wpiutil.log import BooleanLogEntry, DoubleLogEntry, IntegerLogEntry, StringLogEntry

_LogEntry = BooleanLogEntry | DoubleLogEntry | IntegerLogEntry | StringLogEntry
_MISSING = object()


class Logger:
    """Log event messages through WPILib's DataLogManager."""

    enabled: bool = False

    def setup(self) -> None:
        """Start WPILib's data logger when logging is enabled."""
        self._entries: dict[str, _LogEntry] = {}
        if self.enabled:
            wpilib.DataLogManager.start()
            self._data_log = wpilib.DataLogManager.getLog()

    def execute(self) -> None:
        """A Magicbot component requires an execute method.  This does nothing."""
        pass

    @overload
    def log(self, message: str) -> None: ...

    @overload
    def log(self, name: str, value: str | bool | int | float) -> None: ...

    def log(self, name: str, value: object = _MISSING) -> None:
        """Log a message or append a named typed value if enabled.

        A single string argument is written to the DataLogManager's messages
        entry. With two arguments, ``name`` identifies a typed data-log entry.

        Raises:
            TypeError: If the value type is unsupported or the name was
                previously used for a different value type.

        """
        if value is not _MISSING and not isinstance(value, (str, bool, int, float)):
            raise TypeError(
                "Logger values must be strings, booleans, integers, or floats"
            )

        if not self.enabled:
            return

        if value is _MISSING:
            wpilib.DataLogManager.log(name)
            return

        if isinstance(value, bool):
            entry = self._entries.get(name)
            if entry is None:
                entry = BooleanLogEntry(self._data_log, name)
                self._entries[name] = entry
            elif not isinstance(entry, BooleanLogEntry):
                raise TypeError(f"Log entry {name!r} was created with another type")
            entry.append(value)
        elif isinstance(value, int):
            entry = self._entries.get(name)
            if entry is None:
                entry = IntegerLogEntry(self._data_log, name)
                self._entries[name] = entry
            elif not isinstance(entry, IntegerLogEntry):
                raise TypeError(f"Log entry {name!r} was created with another type")
            entry.append(value)
        elif isinstance(value, float):
            entry = self._entries.get(name)
            if entry is None:
                entry = DoubleLogEntry(self._data_log, name)
                self._entries[name] = entry
            elif not isinstance(entry, DoubleLogEntry):
                raise TypeError(f"Log entry {name!r} was created with another type")
            entry.append(value)
        else:
            entry = self._entries.get(name)
            if entry is None:
                entry = StringLogEntry(self._data_log, name)
                self._entries[name] = entry
            elif not isinstance(entry, StringLogEntry):
                raise TypeError(f"Log entry {name!r} was created with another type")
            entry.append(value)
