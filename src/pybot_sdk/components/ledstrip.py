"""Show colors and animated patterns on an addressable LED strip.

In a RobotPy MagicBot project, declare the component and set its configuration
in ``createObjects``. The examples below show the two supported connections.

For a strip connected to a CTRE CANdle::

    from components.ledstrip import LedStrip
    from magicbot import MagicRobot

    class Robot(MagicRobot):
        led_strip: LedStrip

        def createObjects(self):
            self.led_strip_led_count = 60
            self.led_strip_use_candle = True
            self.led_strip_candle_can_id = 1

        def teleopPeriodic(self):
            self.led_strip.color = "blue"
            self.led_strip.mode = "chase"

For a strip connected to a roboRIO PWM port::

    from components.ledstrip import LedStrip
    from magicbot import MagicRobot

    class Robot(MagicRobot):
        led_strip: LedStrip

        def createObjects(self):
            self.led_strip_led_count = 60
            self.led_strip_use_candle = False
            self.led_strip_pwm_port = 0

        def teleopPeriodic(self):
            self.led_strip.color = "green"
            self.led_strip.mode = "blink"

``led_count`` is the number of LEDs on the strip. Use ``use_candle`` to choose
the CANdle; set ``candle_can_id`` for its CAN ID or ``pwm_port`` for the
roboRIO port. A roboRIO addressable LED strip connects to a PWM header, not a
DIO port. Set ``color`` and ``mode`` to string names from the dictionaries on
``LedStrip``. Unknown names display black with the strip off.
"""

import random
from collections.abc import Callable

import wpilib

Pixel = tuple[int, int, int]
Frame = list[Pixel]


class LedStrip:
    """Control an addressable LED strip from MagicBot."""

    # Injected variables
    led_count: int
    use_candle: bool = False
    pwm_port: int = 0
    candle_can_id: int = 0

    def __init__(self) -> None:
        """Start with a black strip turned off."""
        self.color = "black"
        self.mode = "off"
        self.COLORS: dict[str, Pixel] = {
            "black": (0, 0, 0),
            "red": (255, 0, 0),
            "orange": (255, 80, 0),
            "yellow": (255, 200, 0),
            "green": (0, 255, 0),
            "cyan": (0, 255, 255),
            "blue": (0, 0, 255),
            "purple": (150, 0, 255),
            "pink": (255, 20, 120),
            "white": (255, 255, 255),
        }
        self.modes: dict[str, Callable[[Pixel, float], Frame]] = {
            "off": self._frame_off,
            "on": self._frame_on,
            "blink": self._frame_blink,
            "sparkle": self._frame_sparkle,
            "chase": self._frame_chase,
            "knightrider": self._frame_knightrider,
        }
        self.BLINK_PERIOD = 0.5
        self.SPARKLE_CHANCE = 0.05
        self.SPARKLE_FADE = 0.75
        self.SPARKLE_UPDATE_TIME = 0.04
        self.CHASE_LENGTH = 4
        self.CHASE_SPEED = 20
        self.KNIGHT_TAIL_LENGTH = 6
        self.KNIGHT_SPEED = 30

    @property
    def color(self) -> str:
        """Return the selected color name."""
        return self._color

    @color.setter
    def color(self, color: str) -> None:
        """Store color names in lowercase."""
        self._color = color.lower()

    @property
    def mode(self) -> str:
        """Return the selected mode name."""
        return self._mode

    @mode.setter
    def mode(self, mode: str) -> None:
        """Store mode names in lowercase."""
        self._mode = mode.lower()

    def setup(self) -> None:
        """Create the hardware object after MagicBot has set the configuration."""
        # Choose the hardware once; the animation code works the same for both.
        if self.use_candle:
            self._hardware = _CandleBackend(self.candle_can_id, self.led_count)
        else:
            self._hardware = _RoboRioBackend(self.pwm_port, self.led_count)

        self._sparkle_levels = [0.0] * self.led_count
        self._last_sparkle_time = 0.0

    def execute(self) -> None:
        """Build and send the next frame of LEDs."""
        # Using elapsed time keeps animation speed steady if loop timing varies.
        now = wpilib.Timer.getFPGATimestamp()
        base = self.COLORS.get(self.color, self.COLORS["black"])
        frame = self.modes.get(self.mode, self._frame_off)(base, now)
        self._hardware.show(frame)

    def _frame_off(self, base: Pixel, now: float) -> Frame:
        """Every LED dark."""
        return [self.COLORS["black"]] * self.led_count

    def _scale(self, pixel: Pixel, brightness: float) -> Pixel:
        """Dim a pixel. Brightness is from 0.0 (dark) to 1.0 (full)."""
        r, g, b = pixel
        return (int(r * brightness), int(g * brightness), int(b * brightness))

    def _frame_on(self, base: Pixel, now: float) -> Frame:
        """Every LED the same solid color."""
        return [base] * self.led_count

    def _frame_blink(self, base: Pixel, now: float) -> Frame:
        """Whole strip on for half the period, off for the other half."""
        # The remainder repeats the time from zero to BLINK_PERIOD.
        time_in_cycle = now % self.BLINK_PERIOD
        if time_in_cycle < self.BLINK_PERIOD / 2:
            return self._frame_on(base, now)
        return self._frame_off(base, now)

    def _frame_sparkle(self, base: Pixel, now: float) -> Frame:
        """Random LEDs flash to full brightness, then fade out."""
        # Fade the old lights and randomly turn on new ones at a slower rate.
        if now - self._last_sparkle_time >= self.SPARKLE_UPDATE_TIME:
            self._last_sparkle_time = now
            for i in range(self.led_count):
                self._sparkle_levels[i] *= self.SPARKLE_FADE
                if random.random() < self.SPARKLE_CHANCE:
                    self._sparkle_levels[i] = 1.0

        return [self._scale(base, level) for level in self._sparkle_levels]

    def _frame_chase(self, base: Pixel, now: float) -> Frame:
        """Move a group of LEDs down the strip and wrap it to the start."""
        frame = self._frame_off(base, now)
        # Modulo sends the animation back to LED 0 after it reaches the end.
        start = int(now * self.CHASE_SPEED) % self.led_count

        for i in range(self.CHASE_LENGTH):
            frame[(start + i) % self.led_count] = base
        return frame

    def _frame_knightrider(self, base: Pixel, now: float) -> Frame:
        """Move a bright dot back and forth with a fading tail."""
        frame = self._frame_off(base, now)
        last_led = self.led_count - 1
        if last_led < 1:
            return self._frame_on(base, now)

        # A trip goes from the first LED to the last, then back again.
        trip_length = 2 * last_led
        position_in_trip = (now * self.KNIGHT_SPEED) % trip_length

        if position_in_trip <= last_led:
            head = position_in_trip
            direction = 1
        else:
            head = trip_length - position_in_trip
            direction = -1

        head = int(round(head))

        for i in range(self.KNIGHT_TAIL_LENGTH):
            index = head - direction * i
            if 0 <= index <= last_led:
                brightness = 1.0 - i / self.KNIGHT_TAIL_LENGTH
                frame[index] = self._scale(base, brightness)
        return frame


class _RoboRioBackend:
    """LED strip wired to a roboRIO PWM port using WPILib's AddressableLED."""

    def __init__(self, port: int, led_count: int):
        self.led = wpilib.AddressableLED(port)
        self.led.setLength(led_count)
        self.buffer = [wpilib.AddressableLED.LEDData(0, 0, 0) for _ in range(led_count)]
        self.led.setData(self.buffer)
        self.led.start()

    def show(self, frame: Frame) -> None:
        for i, (r, g, b) in enumerate(frame):
            self.buffer[i].setRGB(r, g, b)
        self.led.setData(self.buffer)


class _CandleBackend:
    """LED strip connected to a CTRE CANdle using Phoenix 6."""

    ONBOARD_LEDS = 8  # The strip starts after the LEDs built into the CANdle.

    def __init__(self, can_id: int, led_count: int):
        from phoenix6.controls import SolidColor
        from phoenix6.hardware import CANdle
        from phoenix6.signals import RGBWColor

        self._SolidColor = SolidColor
        self._RGBWColor = RGBWColor
        self.candle = CANdle(can_id)
        self.last_frame = [None] * led_count

    def show(self, frame: Frame) -> None:
        for i, pixel in enumerate(frame):
            if pixel == self.last_frame[i]:
                continue
            self.last_frame[i] = pixel
            index = i + self.ONBOARD_LEDS
            r, g, b = pixel
            request = self._SolidColor(index, index).with_color(
                self._RGBWColor(r, g, b)
            )
            self.candle.set_control(request)
