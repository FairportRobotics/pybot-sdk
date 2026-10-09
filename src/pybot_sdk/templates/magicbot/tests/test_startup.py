"""Startup checks for the generated MagicBot robot."""


def test_robot_starts_disabled(control) -> None:
    """Verify the robot starts and advances while the Driver Station is disabled."""
    with control.run_robot():
        control.step_timing(seconds=0.2, autonomous=False, enabled=False)

        assert control.robot_is_alive
