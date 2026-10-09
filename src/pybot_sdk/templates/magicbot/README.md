# MagicBot Robot Project

This project uses ordinary RobotPy and MagicBot APIs. The SDK is not required
at robot runtime.

## Setup and Tests

Use Python 3.14 for this RobotPy 2026 template:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install robotpy==2026.2.2
robotpy test --no-isolation
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Hardware Map

Edit `config/hardware.yml` to record reviewed CAN assignments and the driver
controller port. With the SDK CLI installed in this development environment,
validate the map before testing or deploying:

```sh
pybot hardware validate config/hardware.yml
pybot hardware generate config/hardware.yml --output hardware_map.py
```

Generation is deterministic and produces plain Python data; robot code does
not load YAML. `hardware_map.py` is generated from the sample map and should
be regenerated and committed with `config/hardware.yml` whenever assignments
change; do not edit the generated module by hand.

The tests inject simulated Xbox input through the MagicBot lifecycle, check a
simulated WPILib PWM output, and verify the component clears its command when
the Driver Station disables the robot. This is a software behavior check, not
an E-stop or physical safety certification. A clean simulation is the MVP
compatibility proxy for roboRIO operation; physical deployment has not yet
been verified.

## Deploy

Connect to the team's robot network, then use RobotPy's existing deploy
command:

```sh
robotpy deploy
```

Before movement tests, follow the team's mentor-reviewed bring-up and safety
checklist. Simulation does not replace inspection or physical safety checks.

## File Ownership

- `robot.py` and `tests/`: student-owned robot behavior and tests.
- `config/hardware.yml`: student-edited hardware assignments; review changes
  with the team before deployment.
- `hardware_map.py`: SDK-generated data consumed by robot code; regenerate it
  from the YAML source rather than editing it directly.
- `pyproject.toml`, `physics.py`, and this README: generated starting files;
  safe to edit. The physics hook models no mechanism dynamics.