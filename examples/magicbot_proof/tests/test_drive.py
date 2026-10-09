"""End-to-end logic simulation for the MagicBot proof project."""

import pytest
from wpilib.simulation import PWMSim, XboxControllerSim


def test_controller_input_reaches_magicbot_component_output(control) -> None:
    """Exercise teleop input through the real component and output path."""
    controller = XboxControllerSim(0)
    motor = PWMSim(0)

    with control.run_robot():
        control.step_timing(seconds=0.2, autonomous=False, enabled=True)
        controller.setLeftY(0.6)
        controller.notifyNewData()
        control.step_timing(seconds=0.6, autonomous=False, enabled=True)

        assert motor.getSpeed() == pytest.approx(0.6, abs=1e-3)
