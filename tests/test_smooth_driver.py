# ruff: noqa: D102, D103, D107
"""Tests for SmoothDriver, using a fake gyro and a simple simulated robot.

Run from the project root with ``python -m pytest tests``.
"""

import math

import pytest
from components.smooth_driver import SmoothDriver
from magicbot.magic_tunable import setup_tunables
from wpimath.geometry import Rotation2d

slew_scalar = SmoothDriver.slew_scalar
slew_vector = SmoothDriver.slew_vector

DT = 0.02


class FakeGyro:
    """Stands in for the Gyro component; tests set the heading and rate."""

    def __init__(self):
        self.rotation = Rotation2d()
        self.rate_dps = 0.0
        self._connected = True

    def connected(self) -> bool:
        return self._connected


class Harness:
    """Runs SmoothDriver in a loop with an ideal, instantly responding robot.

    Each step feeds the driver's commanded rotation back into the gyro, the
    same way a perfect drivetrain would. ``disturbance_dps`` adds an extra
    turn rate, like being bumped or a wheel scrubbing.
    """

    def __init__(self):
        self.gyro = FakeGyro()
        self.driver = SmoothDriver()
        self.driver.gyro = self.gyro
        self.driver.control_loop_wait_time = DT
        setup_tunables(self.driver, "smooth_driver")
        self.driver.setup()
        self.disturbance_dps = 0.0

    def step(self, fwd=0.0, strafe=0.0, rot=0.0, n=1):
        for _ in range(n):
            self.driver.drive(fwd, strafe, rot)
            self.driver.execute()
            rate = math.degrees(self.driver.speeds.omega) + self.disturbance_dps
            self.gyro.rate_dps = rate
            self.gyro.rotation = self.gyro.rotation + Rotation2d.fromDegrees(rate * DT)
        return self.driver.speeds

    @property
    def speeds(self):
        return self.driver.speeds


@pytest.fixture
def h():
    return Harness()


# -- Helpers ----------------------------------------------------------------


def test_slew_scalar_limits_step_and_uses_decel_to_slow():
    assert slew_scalar(0.0, 10.0, accel=5.0, decel=20.0, dt=DT) == pytest.approx(0.1)
    assert slew_scalar(1.0, 0.0, accel=5.0, decel=20.0, dt=DT) == pytest.approx(0.6)
    # Reversing counts as slowing down first.
    assert slew_scalar(1.0, -1.0, accel=5.0, decel=20.0, dt=DT) == pytest.approx(0.6)


def test_slew_vector_limits_length_and_keeps_direction():
    x, y = slew_vector((0.0, 0.0), (3.0, 4.0), accel=10.0, decel=10.0, dt=DT)
    assert math.hypot(x, y) == pytest.approx(0.2)
    assert y / x == pytest.approx(4 / 3)


# -- Input shaping ---------------------------------------------------------


def test_inside_deadband_gives_zero(h):
    s = h.step(fwd=0.05, rot=0.05, n=10)
    assert s.vx == 0.0 and s.omega == 0.0


def test_output_ramps_instead_of_jumping(h):
    first = h.step(fwd=1.0).vx
    assert 0.0 < first < 0.5 * h.driver.max_speed_normal


def test_reaches_mode_maximums(h):
    h.step(fwd=1.0, n=100)
    assert h.speeds.vx == pytest.approx(h.driver.max_speed_normal)
    h.driver.set_mode("BOOST")
    h.step(fwd=1.0, n=200)
    assert h.speeds.vx == pytest.approx(h.driver.max_speed_boost)
    h.driver.set_mode("PRECISION")
    h.step(fwd=1.0, n=200)
    assert h.speeds.vx == pytest.approx(h.driver.max_speed_precision)


def test_stops_faster_than_it_speeds_up(h):
    up = next(i for i in range(1000) if h.step(fwd=1.0).vx >= 2.99)
    down = next(i for i in range(1000) if h.step(fwd=0.0).vx <= 0.01)
    assert down < up


def test_diagonal_acceleration_matches_straight(h):
    s = h.step(fwd=0.7071, strafe=0.7071)
    straight = Harness().step(fwd=1.0)
    # Same stick length, so the same speed vector length after one step.
    assert math.hypot(s.vx, s.vy) == pytest.approx(
        math.hypot(straight.vx, straight.vy), rel=0.01
    )


def test_reverse_works(h):
    s = h.step(fwd=-1.0, n=100)
    assert s.vx == pytest.approx(-h.driver.max_speed_normal)


# -- Heading hold ------------------------------------------------------------


def test_no_target_while_driver_is_rotating(h):
    h.step(fwd=1.0, rot=0.8, n=20)
    assert not h.driver.holding_heading


def test_target_captured_only_after_turning_stops(h):
    h.step(fwd=1.0, rot=0.8, n=20)
    h.step(fwd=1.0, rot=0.0)
    # Right after release the robot is still spinning down: no capture yet.
    assert not h.driver.holding_heading
    h.step(fwd=1.0, n=30)
    assert h.driver.holding_heading


def test_hold_resists_disturbance_and_returns(h):
    h.step(fwd=1.0, n=30)
    assert h.driver.holding_heading
    target = h.gyro.rotation.degrees()

    h.disturbance_dps = 30.0
    h.step(fwd=1.0, n=10)
    h.disturbance_dps = 0.0
    assert abs(h.gyro.rotation.degrees() - target) > 1.0

    h.step(fwd=1.0, n=150)
    assert h.gyro.rotation.degrees() == pytest.approx(target, abs=0.5)


def test_hold_works_across_the_180_degree_wrap(h):
    h.gyro.rotation = Rotation2d.fromDegrees(179.0)
    h.step(fwd=1.0, n=30)
    h.disturbance_dps = 40.0
    h.step(fwd=1.0, n=10)  # crosses +180 / -180
    h.disturbance_dps = 0.0
    h.step(fwd=1.0, n=200)
    err = (h.driver._heading_target - h.gyro.rotation).degrees()
    assert abs(err) < 0.5


def test_hold_works_in_reverse(h):
    h.step(fwd=-1.0, n=30)
    assert h.driver.holding_heading
    h.disturbance_dps = 20.0
    h.step(fwd=-1.0, n=10)
    h.disturbance_dps = 0.0
    h.step(fwd=-1.0, n=150)
    assert abs(h.driver._heading_error_rad) < math.radians(0.5)


def test_target_clears_when_translation_stops(h):
    h.step(fwd=1.0, n=30)
    assert h.driver.holding_heading
    h.step(fwd=0.0)
    assert not h.driver.holding_heading


def test_stopped_robot_does_not_fight_a_bump(h):
    h.step(fwd=1.0, n=30)
    h.step(fwd=0.0, n=60)
    h.disturbance_dps = 30.0
    h.step(n=5)
    h.disturbance_dps = 0.0
    s = h.step(n=20)
    assert s.omega == pytest.approx(0.0, abs=1e-6)


def test_rotation_clears_target_and_driver_steers(h):
    h.step(fwd=1.0, n=30)
    assert h.driver.holding_heading
    s = h.step(fwd=1.0, rot=1.0, n=60)
    assert not h.driver.holding_heading
    assert s.omega == pytest.approx(h.driver.max_rot_normal)


def test_hold_disabled_when_gyro_disconnected(h):
    h.gyro._connected = False
    h.step(fwd=1.0, n=40)
    assert not h.driver.holding_heading


def test_hold_correction_is_clamped(h):
    h.step(fwd=1.0, n=30)
    h.gyro.rotation = h.gyro.rotation + Rotation2d.fromDegrees(120)
    s = h.step(fwd=1.0)
    limit = h.driver.max_rot_normal * h.driver.hold_max_fraction
    assert abs(s.omega) <= limit + 1e-9


def test_reset_clears_state(h):
    h.step(fwd=1.0, n=30)
    h.driver.reset()
    assert not h.driver.holding_heading
    assert h.driver.speeds.vx == 0.0


# -- Mode strings -------------------------------------------------------------


def test_modes_are_strings_and_case_insensitive(h):
    h.driver.set_mode("Boost")
    assert h.driver.mode == "boost"
    h.driver.set_mode("PRECISION")
    assert h.driver.mode_name() == "precision"


def test_unknown_mode_raises(h):
    with pytest.raises(ValueError):
        h.driver.set_mode("turbo")
