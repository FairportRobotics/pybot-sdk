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