# pybot-sdk

`pybot-sdk` provides development-time tools for RobotPy projects. It does not
replace RobotPy's project, test, simulation, or deployment commands.

Install the SDK and scaffold the MagicBot starter project:

```sh
python -m pip install .
pybot new robot-project --template magicbot
```

The starter template targets Python 3.14 and RobotPy 2026. Its RobotPy
simulation test is the MVP compatibility proxy for roboRIO operation; physical
deployment remains unverified until a roboRIO is available.

The project is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).