"""End-to-end logic simulation for the MagicBot proof project."""

import pytest
from wpilib.simulation import PWMSim, XboxControllerSim


def test_controller_input_reaches_magicbot_component_output(control) -> None:
    """Verify controller input drives output and disable removes the command."""
    controller = XboxControllerSim(0)
    motor = PWMSim(0)

    with control.run_robot():
        control.step_timing(seconds=0.2, autonomous=False, enabled=True)
        controller.setLeftY(0.6)
        controller.notifyNewData()
        control.step_timing(seconds=0.6, autonomous=False, enabled=True)

        assert motor.getSpeed() == pytest.approx(0.6, abs=1e-3)

        control.step_timing(seconds=0.2, autonomous=False, enabled=False)

        assert motor.getSpeed() == pytest.approx(0.0, abs=1e-3)
