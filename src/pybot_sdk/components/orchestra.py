"""Play music through a CTRE motor using Phoenix 6 Orchestra.

Orchestra makes a motor spin at carefully chosen speeds so it produces musical
tones. It does not use a regular speaker. First, turn a MIDI song into a
``.chrp`` file with CTRE Phoenix Tuner, then put that file in the robot
project's ``src/main/deploy`` folder.

In a RobotPy MagicBot project, create a Talon FX and choose the song in
``createObjects``::

    import phoenix6
    from components.orchestra import Orchestra
    from magicbot import MagicRobot

    class Robot(MagicRobot):
        orchestra: Orchestra

        def createObjects(self):
            self.orchestra_motor = phoenix6.hardware.TalonFX(1)
            self.orchestra_music_file = "school_song.chrp"

        def teleopInit(self):
            self.orchestra.play()

Call ``play()`` to start or resume the song, ``pause()`` to pause it, and
``stop()`` to stop it and return to the beginning. ``is_playing()`` tells you
whether the song is playing.

The robot must be enabled for Orchestra to play. While playing, Orchestra
controls the motor, so do not use that same motor for driving or another task
at the same time. This component uses one motor for one track.
"""

from typing import Any

from magicbot import feedback


class Orchestra:
    """Play a deployed CTRE Chirp music file through a Talon FX motor."""

    # MagicBot injects these from robot attributes named after the component.
    motor: Any
    music_file: str

    def setup(self) -> None:
        """Connect the motor and load its music file."""
        if not self.music_file.strip():
            raise ValueError("orchestra_music_file must name a .chrp music file")

        from phoenix6 import orchestra as phoenix_orchestra

        self._player = phoenix_orchestra.Orchestra()
        self._check_status(self._player.add_instrument(self.motor), "add the motor")
        self._check_status(
            self._player.load_music(self.music_file),
            f"load the music file {self.music_file!r}",
        )

    def play(self) -> None:
        """Start the song, or continue from where it was paused."""
        self._check_status(self._player.play(), "play the music")

    def pause(self) -> None:
        """Pause the song so that it can continue from the same place later."""
        self._check_status(self._player.pause(), "pause the music")

    def stop(self) -> None:
        """Stop the song and reset it to the beginning."""
        self._check_status(self._player.stop(), "stop the music")

    @feedback
    def is_playing(self) -> bool:
        """Show whether the motor is currently playing the song."""
        return self._player.is_playing()

    @staticmethod
    def _check_status(status: Any, action: str) -> None:
        """Raise a readable error if Phoenix 6 could not complete an action."""
        if not status.is_ok():
            raise RuntimeError(f"CTRE Orchestra could not {action}: {status}")
