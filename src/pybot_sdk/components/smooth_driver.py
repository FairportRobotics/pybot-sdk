"""Turn raw joystick values into smooth, drivetrain-independent speed commands.

SmoothDriver sits between the driver's joysticks and the drivetrain. It does
not move any motors. Each loop it produces a ``ChassisSpeeds`` that either a
swerve drivetrain or a west coast (differential) drivetrain can use.

What it does, in order:

1. **Deadband** removes stick drift near the center.
2. **Response curve** gives finer control at low stick values.
3. **Mode scaling** multiplies by the maximum for the current mode
   ("normal", "boost", or "precision").
4. **Slew limiting** ramps the output toward the target instead of jumping,
   and lets the robot slow down faster than it speeds up.
5. **Heading hold** keeps the robot pointed straight when the driver is
   translating but not rotating.

Heading hold rules:

* Rotation stick used: the heading target is cleared and the driver steers.
* Rotation stick centered and translating: after the robot has stopped
  turning for ``settle_time`` seconds, the current heading becomes the target
  and a PID holds it.
* Not translating: the target is cleared, so the robot never fights to return
  to an old heading after being bumped while stopped.
* Gyro disconnected: heading hold is turned off.

Usage in a RobotPy MagicBot project. Declare the gyro first, then
SmoothDriver, then the drivetrain, because MagicBot runs components in the
order they are declared::

    from components.gyro import Gyro
    from components.smooth_driver import SmoothDriver

    class Robot(MagicRobot):
        gyro: Gyro
        smooth_driver: SmoothDriver
        drivetrain: TankDrive  # or SwerveDrive

        def teleopInit(self):
            self.gyro.reset()
            self.smooth_driver.reset()

        def teleopPeriodic(self):
            if self.stick.getRightBumper():
                self.smooth_driver.set_mode("boost")
            elif self.stick.getLeftBumper():
                self.smooth_driver.set_mode("precision")
            else:
                self.smooth_driver.set_mode("normal")

            # Joysticks report up and right as negative/positive, so flip the
            # signs to get forward-positive, left-positive, CCW-positive.
            self.smooth_driver.drive(
                fwd=-self.stick.getLeftY(),
                strafe=0.0,  # west coast drivetrains ignore this
                rot=-self.stick.getRightX(),
            )

The drivetrain then reads ``self.smooth_driver.speeds`` in its own
``execute()``. Because the drivetrain is declared after SmoothDriver, the value
is current for this loop.

All tunables (maximums, slew rates, heading hold gains) appear in
NetworkTables under ``/components/smooth_driver`` and can be changed live.
Speeds are in m/s and rad/s.

``control_loop_wait_time`` is the loop period. MagicBot's default is 0.02 s.
If your Robot class sets a different ``control_loop_wait_time``, MagicBot
passes it in automatically.
"""

from __future__ import annotations

import math

from components.gyro import Gyro
from magicbot import feedback, tunable, will_reset_to
from wpimath import applyDeadband
from wpimath.controller import PIDController
from wpimath.kinematics import ChassisSpeeds

# ---------------------------------------------------------------------------
# MagicBot component


class SmoothDriver:
    """Condition joystick input and hold heading when driving straight."""

    # Injected by MagicBot
    gyro: Gyro
    control_loop_wait_time: float = 0.02

    # Input shaping
    deadband = tunable(0.08)
    translation_curve = tunable(2.0)  # 1.0 = linear, 2.0 = squared
    rotation_curve = tunable(2.0)

    # Maximums per mode (real units)
    max_speed_normal = tunable(3.0)  # m/s
    max_speed_boost = tunable(4.5)
    max_speed_precision = tunable(1.0)
    max_rot_normal = tunable(3.0)  # rad/s
    max_rot_boost = tunable(4.0)
    max_rot_precision = tunable(1.5)

    # Slew rates (base values, normal mode)
    translation_accel = tunable(6.0)  # m/s^2
    translation_decel = tunable(12.0)  # m/s^2, faster so the driver can stop
    rotation_accel = tunable(12.0)  # rad/s^2
    rotation_decel = tunable(20.0)  # rad/s^2

    # Slew rate multipliers for the other modes
    boost_slew_scale = tunable(0.75)  # gentler, protects traction at speed
    precision_slew_scale = tunable(0.5)  # gentler, for fine positioning

    # Heading hold
    heading_hold_enabled = tunable(True)
    hold_kp = tunable(4.0)  # rad/s of correction per rad of error
    hold_ki = tunable(0.0)
    hold_kd = tunable(0.0)
    settle_rate_dps = tunable(8.0)  # must turn slower than this to capture
    settle_time = tunable(0.1)  # seconds below settle_rate_dps to capture
    hold_max_fraction = tunable(0.6)  # hold correction limit, fraction of max rot

    # Inputs, cleared to 0 every loop so stale values can't stick
    fwd_input = will_reset_to(0.0)
    strafe_input = will_reset_to(0.0)
    rot_input = will_reset_to(0.0)

    @staticmethod
    def apply_curve(value: float, exponent: float) -> float:
        """Reshape a stick value while keeping its sign and the -1..1 range."""
        return math.copysign(abs(value) ** exponent, value)

    @staticmethod
    def slew_scalar(
        current: float, target: float, accel: float, decel: float, dt: float
    ) -> float:
        """Move ``current`` toward ``target`` without exceeding the allowed rate.

        ``accel`` applies when speed is growing away from zero. ``decel``
        applies when speed is shrinking or reversing. Both are positive, in
        units per second squared.
        """
        speeding_up = abs(target) > abs(current) and (
            current == 0.0 or math.copysign(1.0, target) == math.copysign(1.0, current)
        )
        max_step = (accel if speeding_up else decel) * dt
        return current + max(-max_step, min(max_step, target - current))

    @staticmethod
    def slew_vector(
        current: tuple[float, float],
        target: tuple[float, float],
        accel: float,
        decel: float,
        dt: float,
    ) -> tuple[float, float]:
        """Move a 2D vector toward a target, limiting the size of the change.

        Limiting the whole vector (instead of x and y separately) makes
        diagonal acceleration feel the same as straight-line acceleration.
        """
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        distance = math.hypot(dx, dy)
        if distance < 1e-9:
            return target

        speeding_up = math.hypot(*target) > math.hypot(*current)
        max_step = (accel if speeding_up else decel) * dt
        if distance <= max_step:
            return target
        scale = max_step / distance
        return (current[0] + dx * scale, current[1] + dy * scale)

    def setup(self) -> None:
        """Create the controller and start from a stopped state."""
        self._mode = "normal"
        self._hold_pid = PIDController(self.hold_kp, self.hold_ki, self.hold_kd)
        self.reset()

    # -- Public API --------------------------------------------------------

    def reset(self) -> None:
        """Stop the output and forget any heading target.

        Call this from ``teleopInit`` (after ``gyro.reset()``) and any time
        you re-zero the gyro, so an old target can't linger.
        """
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0
        self._heading_target = None
        self._settle_elapsed = 0.0
        self._heading_error_rad = 0.0
        self._hold_pid.reset()
        self.speeds = ChassisSpeeds()

    def set_mode(self, mode: str) -> None:
        """Choose "normal", "boost", or "precision" for the next loop.

        The class constants ``SmoothDriver.NORMAL``, ``BOOST`` and
        ``PRECISION`` hold these strings and avoid typos. Names are not case
        sensitive. Raises ValueError for an unknown mode.
        """
        cleaned = mode.strip().lower()
        valid_modes = ("normal", "boost", "precision")
        if cleaned not in valid_modes:
            raise ValueError(f"Unknown mode {mode!r}; valid options: {valid_modes}")
        self._mode = cleaned

    def drive(self, fwd: float, strafe: float, rot: float) -> None:
        """Provide raw stick values, each from -1 to 1.

        Forward is positive, left is positive, and counterclockwise is
        positive. Call this every loop from ``teleopPeriodic``.
        """
        self.fwd_input = fwd
        self.strafe_input = strafe
        self.rot_input = rot

    @property
    def mode(self) -> str:
        """Return the current driving mode."""
        return self._mode

    @property
    def holding_heading(self) -> bool:
        """Return whether a heading target is currently being held."""
        return self._heading_target is not None

    # -- Feedback for dashboards ------------------------------------------

    @feedback
    def mode_name(self) -> str:
        """Show the current drive mode."""
        return self._mode

    @feedback
    def holding(self) -> bool:
        """Show whether heading hold is active."""
        return self.holding_heading

    @feedback
    def heading_target_degrees(self) -> float:
        """Show the heading target, or NaN when there is none."""
        if self._heading_target is None:
            return math.nan
        return self._heading_target.degrees()

    @feedback
    def heading_error_degrees(self) -> float:
        """Show the heading error while holding."""
        return math.degrees(self._heading_error_rad)

    # -- Internals ---------------------------------------------------------

    def _mode_limits(self) -> tuple[float, float, float]:
        """Return (max speed, max rotation, slew scale) for the current mode."""
        if self._mode == "boost":
            return (self.max_speed_boost, self.max_rot_boost, self.boost_slew_scale)
        if self._mode == "precision":
            return (
                self.max_speed_precision,
                self.max_rot_precision,
                self.precision_slew_scale,
            )
        return (self.max_speed_normal, self.max_rot_normal, 1.0)

    def _shape_translation(self) -> tuple[float, float]:
        """Deadband and curve the translation stick as one vector.

        The deadband is applied to the vector's length, so pushing the stick
        diagonally doesn't change where the dead zone ends.
        """
        magnitude = math.hypot(self.fwd_input, self.strafe_input)
        if magnitude < 1e-9:
            return (0.0, 0.0)
        shaped = self.apply_curve(
            applyDeadband(min(magnitude, 1.0), self.deadband), self.translation_curve
        )
        scale = shaped / magnitude  # keeps direction, even past a 1.0 corner
        return (self.fwd_input * scale, self.strafe_input * scale)

    def _shape_rotation(self) -> float:
        """Deadband and curve the rotation stick."""
        return self.apply_curve(
            applyDeadband(max(-1.0, min(1.0, self.rot_input)), self.deadband),
            self.rotation_curve,
        )

    def _update_heading_hold(
        self, rotating: bool, translating: bool, dt: float, max_rot: float
    ) -> float | None:
        """Run the heading hold rules.

        Returns a rotation command in rad/s when the hold is steering, or
        None when the driver (or a stopped robot) is in control.
        """
        gyro_ok = self.gyro.connected()

        if rotating or not translating or not gyro_ok or not self.heading_hold_enabled:
            self._heading_target = None
            self._settle_elapsed = 0.0
            self._heading_error_rad = 0.0
            return None

        if self._heading_target is None:
            # Wait until the robot has really stopped turning before locking
            # on, otherwise we would grab a heading mid-turn and overshoot.
            if abs(self.gyro.rate_dps) < self.settle_rate_dps:
                self._settle_elapsed += dt
            else:
                self._settle_elapsed = 0.0

            if self._settle_elapsed < self.settle_time:
                return None

            self._heading_target = self.gyro.rotation
            self._hold_pid.reset()

        # Rotation2d subtraction wraps to +/- pi, so no continuous-input
        # PID is needed. Error is the shortest turn from heading to target.
        error = (self._heading_target - self.gyro.rotation).radians()
        self._heading_error_rad = error
        self._hold_pid.setP(self.hold_kp)
        self._hold_pid.setD(self.hold_kd)
        # PIDController computes (setpoint - measurement), so measurement 0
        # and setpoint = error gives a command that turns toward the target.
        correction = self._hold_pid.calculate(0.0, error)
        limit = max_rot * self.hold_max_fraction
        return max(-limit, min(limit, correction))

    # -- MagicBot calls this every loop -----------------------------------

    def execute(self) -> None:
        """Compute this loop's smoothed ``ChassisSpeeds``."""
        dt = self.control_loop_wait_time
        max_speed, max_rot, slew_scale = self._mode_limits()

        # 1-3. Shape the sticks and scale to real units.
        tx, ty = self._shape_translation()
        target_vx = tx * max_speed
        target_vy = ty * max_speed
        rot_shaped = self._shape_rotation()
        target_omega = rot_shaped * max_rot

        rotating = rot_shaped != 0.0
        translating = (tx != 0.0) or (ty != 0.0)

        # 4a. Slew translation as a vector.
        self._vx, self._vy = self.slew_vector(
            (self._vx, self._vy),
            (target_vx, target_vy),
            self.translation_accel * slew_scale,
            self.translation_decel * slew_scale,
            dt,
        )

        # 5. Heading hold may take over rotation.
        hold_omega = self._update_heading_hold(rotating, translating, dt, max_rot)

        if hold_omega is not None:
            # The PID output is already a smooth, clamped command, and
            # running it through a slew limiter would add lag that can make
            # the hold oscillate. Just keep the limiter's state in sync so
            # handing control back to the driver is smooth.
            self._omega = hold_omega
        else:
            # 4b. Slew rotation (also ramps down after the hold lets go).
            self._omega = self.slew_scalar(
                self._omega,
                target_omega,
                self.rotation_accel * slew_scale,
                self.rotation_decel * slew_scale,
                dt,
            )

        self.speeds = ChassisSpeeds(self._vx, self._vy, self._omega)
