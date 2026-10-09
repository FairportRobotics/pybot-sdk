# MagicBot HAL Proof

This small project verifies the 2026 RobotPy MagicBot lifecycle with Python 3.14. Its test sends simulated Xbox input through a MagicBot component and observes a simulated WPILib PWM output using RobotPy's native test runner:

```sh
robotpy test --no-isolation
```

The PWM actuator is only a logic-simulation probe. This proof does not verify Phoenix/Talon FX simulation, roboRIO deployment, or physical hardware behavior.