"""Give a Magicbot robot the same gyro interface across different sensors.

The component reports counterclockwise-positive heading and turn rate,
regardless of which supported sensor is connected. In a RobotPy MagicBot
project, declare the component and set its hardware configuration in
``createObjects``. For example, to use a Pigeon 2 with CAN ID 1::

    from components.gyro import Gyro
    from magicbot import MagicRobot
    from wpimath.geometry import Rotation2d

    class Robot(MagicRobot):
        gyro: Gyro

        def createObjects(self):
            self.gyro_type = "pigeon2"
            self.gyro_device_id = 1
            self.gyro_bus = ""  # Use the roboRIO's default CAN bus.

        def teleopInit(self):
            self.gyro.reset(Rotation2d())

        def teleopPeriodic(self):
            heading = self.gyro.rotation
            turn_rate_dps = self.gyro.rate_dps

MagicBot creates and runs the declared component. ``gyro_type``,
``gyro_device_id``, and ``gyro_bus`` configure its ``type``, ``device_id``,
and ``bus`` settings. Read ``rotation`` and ``rate_dps`` from other robot
methods or components, and call ``reset`` when you want to choose the reported
heading.

For the SystemCore onboard IMU, set ``type`` to ``"systemcore"`` and ``mount``
to ``"flat"``, ``"landscape"``, or ``"portrait"``, depending on how the board
is mounted.

To add a new gyro, write a reader that provides ``get_heading()``,
``get_turn_rate_dps()``, and ``is_connected()``. Heading and turn rate must be
counterclockwise-positive, and turn rate must be in degrees per second. If the
new sensor has WPILib's ``getAngle()`` and ``getRate()`` methods, you can often
use ``WpilibGyroReader`` to handle the sign conversion. Otherwise, make a new
reader class that converts the sensor's values.

Then write a factory that creates the sensor and returns its reader, and add
the name and factory to ``_GYRO_FACTORIES``. For example, if WPILib has a
``MyGyro`` class with the usual ``getAngle()`` and ``getRate()`` methods::

    def _create_my_gyro(settings: GyroSettings) -> GyroReader:
        gyro = wpilib.MyGyro(settings.device_id)
        return WpilibGyroReader(gyro)

    _GYRO_FACTORIES["mygyro"] = _create_my_gyro

Replace ``MyGyro`` with the real sensor class and use its required settings.
Names are normalized, so users can write ``"mygyro"`` or ``"my-gyro"``.
The simulation uses ``SimulatedGyroReader`` instead of creating hardware;
provide its heading and turn rate with ``set_simulation_readings()``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import degrees
from typing import Callable, Protocol

import wpilib
from magicbot import feedback
from wpimath.geometry import Rotation2d


# ---------------------------------------------------------------------------
# Shared gyro rules and settings
#
# Every gyro must provide the same three readings, even if different brands
# use different method names or units. GyroSettings holds the choices needed
# to create a particular sensor.

class GyroReader(Protocol):
    """The readings that every gyro type must provide."""

    def get_heading(self) -> Rotation2d:
        """Return the direction the robot is facing."""
        ...

    def get_turn_rate_dps(self) -> float:
        """Return how fast the robot is turning, in degrees per second."""
        ...

    def is_connected(self) -> bool:
        """Return whether the gyro source is connected."""
        ...


@dataclass(frozen=True)
class GyroSettings:
    """Settings used to choose and connect to a gyro."""

    device_id: int = 0  # CAN ID (ignored by SPI/I2C gyros)
    bus: str = ""  # CAN bus name for CAN gyros, or "spi"/"i2c" for navx
    mount: str = "flat"  # SystemCore IMU only: flat | landscape | portrait


# ---------------------------------------------------------------------------
# Readers for individual gyro types
#
# Each reader translates one sensor's readings into the shared GyroReader
# format. The rest of the robot can then use one set of method names and units.

class Pigeon2GyroReader:
    """Read the heading and turn rate from a CTRE Pigeon 2."""

    def __init__(self, pigeon):
        """Save the Pigeon signals used to read heading and turn rate."""
        self._heading_signal = pigeon.get_yaw()
        self._turn_rate_signal = pigeon.get_angular_velocity_z_world()

    def get_heading(self) -> Rotation2d:
        """Return the latest Pigeon heading."""
        return Rotation2d.fromDegrees(self._heading_signal.refresh().value_as_double)

    def get_turn_rate_dps(self) -> float:
        """Return the latest turn rate in degrees per second."""
        return self._turn_rate_signal.refresh().value_as_double

    def is_connected(self) -> bool:
        """Return whether the Pigeon heading signal reports an OK status."""
        return self._heading_signal.status.is_ok()


class SimulatedGyroReader:
    """Hold gyro readings provided by the robot's simulation."""

    def __init__(self):
        """Start with the robot facing forward and not turning."""
        self._heading = Rotation2d()
        self._turn_rate_dps = 0.0

    def set_readings(self, heading: Rotation2d, turn_rate_dps: float) -> None:
        """Update the simulated heading and turn rate."""
        self._heading = heading
        self._turn_rate_dps = turn_rate_dps

    def get_heading(self) -> Rotation2d:
        """Return the simulated heading."""
        return self._heading

    def get_turn_rate_dps(self) -> float:
        """Return the simulated turn rate in degrees per second."""
        return self._turn_rate_dps

    def is_connected(self) -> bool:
        """Report the simulated gyro as connected."""
        return True


class SystemCoreGyroReader:
    """Read heading and turn rate from the SystemCore onboard IMU."""

    def __init__(self, imu):
        """Store the SystemCore IMU."""
        self._imu = imu

    def get_heading(self) -> Rotation2d:
        """Return the IMU yaw, which WPILib reports in radians."""
        return Rotation2d(self._imu.get_yaw())

    def get_turn_rate_dps(self) -> float:
        """Return the Z-axis turn rate converted from radians to degrees."""
        return degrees(self._imu.get_gyro_rate_z())

    def is_connected(self) -> bool:
        """Report connected because this IMU does not expose connection status."""
        return True


class WpilibGyroReader:
    """Read angles from gyros that use WPILib's clockwise-positive convention.

    Several WPILib gyro classes expose ``getAngle()`` and ``getRate()``.
    Their sign is opposite to the counterclockwise-positive convention used by
    this component, so this reader flips the signs.
    """

    def __init__(self, gyro, connected: Callable[[], bool] | None = None):
        """Store a WPILib gyro and, if available, its connection check."""
        self._gyro = gyro
        self._connected = connected

    def get_heading(self) -> Rotation2d:
        """Return the robot's heading using counterclockwise-positive angles."""
        return Rotation2d.fromDegrees(-self._gyro.getAngle())

    def get_turn_rate_dps(self) -> float:
        """Return the turn rate using counterclockwise-positive values."""
        return -self._gyro.getRate()

    def is_connected(self) -> bool:
        """Return the callback's status, or assume connected if absent."""
        return self._connected() if self._connected else True


# ---------------------------------------------------------------------------
# Creating a sensor from its name and settings
#
# A factory is a function that builds one sensor. The name-cleaning helper
# lets students type names such as "Pigeon 2" or "pigeon-2" and get the same
# result. Each factory below chooses the right reader for its sensor.

GyroFactory = Callable[[GyroSettings], GyroReader]


def _normalize_gyro_name(name: str) -> str:
    """Remove spaces and punctuation so names are easy to match."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _create_adis16448(settings: GyroSettings) -> GyroReader:
    """Create a reader for the ADIS16448 gyro."""
    imu = wpilib.ADIS16448_IMU()
    return WpilibGyroReader(imu, getattr(imu, "isConnected", None))


def _create_adis16470(settings: GyroSettings) -> GyroReader:
    """Create a reader for the ADIS16470 gyro."""
    imu = wpilib.ADIS16470_IMU()
    return WpilibGyroReader(imu, getattr(imu, "isConnected", None))


def _create_adxrs450(settings: GyroSettings) -> GyroReader:
    """Create a reader for the ADXRS450 gyro."""
    return WpilibGyroReader(wpilib.ADXRS450_Gyro())


def _create_navx(settings: GyroSettings) -> GyroReader:
    """Create a navX reader using SPI by default, or I2C if requested."""
    import navx

    bus = settings.bus.lower() or "spi"
    if bus == "spi":
        ahrs = navx.AHRS.create_spi()
    elif bus == "i2c":
        ahrs = navx.AHRS.create_i2c()
    else:
        raise ValueError(f"navx bus must be 'spi' or 'i2c', got {settings.bus!r}")
    return WpilibGyroReader(ahrs, ahrs.isConnected)


def _create_pigeon2(settings: GyroSettings) -> GyroReader:
    """Create a Pigeon 2 reader."""
    import phoenix6

    pigeon = phoenix6.hardware.Pigeon2(settings.device_id, settings.bus)
    return Pigeon2GyroReader(pigeon)


def _create_systemcore(settings: GyroSettings) -> GyroReader:
    """Create a SystemCore reader using the selected mount orientation."""
    orientations = {
        "flat": wpilib.OnboardIMU.MountOrientation.FLAT,
        "landscape": wpilib.OnboardIMU.MountOrientation.LANDSCAPE,
        "portrait": wpilib.OnboardIMU.MountOrientation.PORTRAIT,
    }
    try:
        orientation = orientations[settings.mount.strip().lower()]
    except KeyError:
        raise ValueError(
            "SystemCore mount must be 'flat', 'landscape', or 'portrait', "
            f"got {settings.mount!r}"
        ) from None
    imu = wpilib.OnboardIMU(orientation)
    return SystemCoreGyroReader(imu)


# Several spellings can be used for the same gyro. Names are normalized
# before lookup, so "Pigeon 2" and "pigeon-2" both match "pigeon2".

_GYRO_FACTORIES: dict[str, GyroFactory] = {
    "adis16448": _create_adis16448,
    "adis16470": _create_adis16470,
    "adxrs450": _create_adxrs450,
    "navx": _create_navx,
    "navx2": _create_navx,
    "navxmxp": _create_navx,
    "pigeon2": _create_pigeon2,
    "pigeon20": _create_pigeon2,
    "systemcore": _create_systemcore,
}


def available_gyro_types() -> list[str]:
    """Return the gyro type names accepted by this component."""
    return sorted(_GYRO_FACTORIES)


# ---------------------------------------------------------------------------
# MagicBot component used by the robot
#
# MagicBot fills in the settings and calls setup() and execute() for us.
# This class keeps the current reading and applies a heading offset when reset
# is called, so the reported direction can start from any angle.

class Gyro:
    """Give the robot one consistent way to read its gyro."""

    # Injected variables
    type: str
    device_id: int = 0
    bus: str = ""
    mount: str = "flat"

    def setup(self):
        """Initialize the heading and choose a hardware or simulated reader."""
        self._heading_offset = Rotation2d()
        self._heading = Rotation2d()
        self._turn_rate_dps = 0.0
        self._reader = self._create_reader()

    def _create_reader(self) -> GyroReader:
        """Choose a reader based on whether the robot is simulated."""
        if wpilib.RobotBase.isSimulation():
            return SimulatedGyroReader()

        try:
            factory = _GYRO_FACTORIES[_normalize_gyro_name(self.type)]
        except KeyError:
            raise ValueError(
                f"Unknown gyro_type {self.type!r}; "
                f"valid options: {available_gyro_types()}"
            ) from None
        settings = GyroSettings(self.device_id, self.bus, self.mount)
        return factory(settings)

    def reset(self, heading: Rotation2d = Rotation2d()):
        """Set the reported heading without changing the gyro's own reading."""
        self._heading_offset = heading - self._reader.get_heading()
        self._heading = heading

    def set_simulation_readings(
        self, heading: Rotation2d, turn_rate_dps: float
    ) -> None:
        """Set the readings produced by the simulated robot.

        Raises:
            RuntimeError: If the component is using a real gyro.

        """
        if not isinstance(self._reader, SimulatedGyroReader):
            raise RuntimeError("Simulation readings require a simulated robot")
        self._reader.set_readings(heading, turn_rate_dps)

    @property
    def rotation(self) -> Rotation2d:
        """Return the robot's current heading as a rotation."""
        return self._heading

    @property
    def rate_dps(self) -> float:
        """Return how fast the robot is turning, in degrees per second."""
        return self._turn_rate_dps

    @feedback
    def heading_degrees(self) -> float:
        """Show the robot's current heading in the MagicBot feedback display."""
        return self._heading.degrees()

    @feedback
    def connected(self) -> bool:
        """Show whether the gyro reader reports a connection."""
        return self._reader.is_connected()

    def execute(self):
        """Update the heading and turn rate from the selected reader."""
        self._heading = self._reader.get_heading() + self._heading_offset
        self._turn_rate_dps = self._reader.get_turn_rate_dps()
