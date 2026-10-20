# pybot-sdk

`pybot-sdk` provides development-time tools for RobotPy projects. It does not
replace RobotPy's project, test, simulation, or deployment commands.

## Install the SDK

To install the wheel attached to the latest GitHub Release (requires the
[GitHub CLI](https://cli.github.com/)):

```sh
gh release download --repo FairportRobotics/pybot-sdk --pattern '*.whl'
python -m pip install ./pybot_sdk-*.whl
```

## Create a starter project

There are four templates that are supported by the SDK.

```sh
# Show the installed SDK version
pybot version

# Create a project in the robot directory
pybot new robot --template magicbot
# or
pybot new robot --template command
# or
pybot new robot --template xrp
# or
pybot new robot --template sysid

# Add components to an existing MagicBot project
pybot add component gyro
pybot add component logger
```

The MagicBot starter template targets Python 3.14 and RobotPy 2026. Its RobotPy
simulation test is the MVP compatibility proxy for roboRIO operation; physical
deployment remains unverified until a roboRIO is available.

The SysId template creates a single-file `TimedRobot` project for characterizing
one configured mechanism with WPILib SysId. Choose "Run SysId" in the
autonomous chooser to run quasistatic forward and backward, followed by dynamic
forward and backward. The chooser defaults to "Do Nothing".

Run `pybot add component <name>` from a project directory to copy a component
template into its `components/` directory. The command reports an error if the
requested component template is not available.

Set `self.logger_enabled = True` in the robot's `createObjects` method to enable
the logger component. It writes messages to WPILib's managed data log and
standard output. To add named values to the data log, call
`self.logger.log("Drive/Speed", 2.5)`; strings, booleans, integers, and floats
are supported. A named entry must keep the same value type for the lifetime of
the logger. See the component documentation for a usage example.

## Development

Install the test and lint tools, then run the SDK tests and Ruff checks:

```sh
python -m pip install -e ".[test]"
python -m pytest
ruff check .
ruff format --check .
python -m build --sdist --wheel
```

Ruff formatting can be applied with `ruff format .`. The generated-project
simulation tests use RobotPy's `--no-isolation` mode because pyfrc's isolated
worker mode stalls intermittently in the current macOS environment. Its native
fixtures still reset HAL and NetworkTables between tests. CI also installs the
built wheel in a clean environment and exercises the packaged CLI and template.

The project is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).