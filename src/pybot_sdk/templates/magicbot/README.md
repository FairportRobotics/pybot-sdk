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

## Deploy

Connect to the team's robot network, then use RobotPy's existing deploy
command:

```sh
robotpy deploy
```

Before movement tests, follow the team's mentor-reviewed bring-up and safety
checklist. Simulation does not replace inspection or physical safety checks.