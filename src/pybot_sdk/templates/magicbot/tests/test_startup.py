def test_robot_starts_disabled(control) -> None:
    with control.run_robot():
        control.step_timing(seconds=0.2, autonomous=False, enabled=False)

        assert control.robot_is_alive