# WPILib SysId Robot Project

This project uses a regular WPILib `TimedRobot` and
`commands2.sysid.SysIdRoutine` to test one mechanism. All robot code and
configuration are together in `robot.py`. The example uses a PWM motor
controller and a quadrature encoder.

## Setup and Deploy

Use a Python version supported by the RobotPy release you are installing.
Open a terminal in the project folder and follow the instructions for your
operating system.

### Windows 

#### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
robotpy deploy
```

#### Command Prompt

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
robotpy deploy
```

### Linux and macOS

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
robotpy deploy
```

## Read and Change `robot.py`

At the top of `robot.py`, change `MOTOR_PWM_PORT`, `ENCODER_A_CHANNEL`, and
`ENCODER_B_CHANNEL` to match your wiring. Set
`ENCODER_DISTANCE_PER_PULSE` to the distance or angle represented by one
encoder pulse. The example value of `1.0` reports encoder counts, which is
usually not a useful physical unit for analysis.

The `robotInit()` method creates the motor and encoder. If your robot uses
different hardware, replace those objects and adjust `apply_voltage()` and
`log_motor_data()` to use that hardware's methods. `apply_voltage()` sends the
test voltage to the motor. `log_motor_data()` records motor voltage, encoder
position, and encoder speed. Use position and speed units that match your
mechanism and the SysId analysis you plan to use. Multiple motors that move
the same mechanism can be controlled and logged together in these methods.

The Driver Station chooser defaults to **Do Nothing**. Select **Run SysId**
only when you are ready to test. During autonomous, the program runs these four
tests in order:

1. Quasistatic forward
2. Quasistatic backward
3. Dynamic forward
4. Dynamic backward

A quasistatic test slowly increases the voltage. A dynamic test applies a
constant voltage step. Forward and backward tell the mechanism which direction
to move.

Before testing, check the wiring, encoder direction, encoder scaling, and
mechanism travel limits. Make sure the robot and mechanism have clear space,
keep people away, and have someone ready to disable the robot. Add any
mechanism-specific hard or software limits needed to prevent damage. Stop the
test right away if the mechanism moves in an unsafe way. The example uses
WPILib's defaults: a 1 V/s quasistatic ramp, a 7 V dynamic step, and a
10-second limit for each test. Choose lower values if your mechanism needs
them.

WPILib writes the test state and motor measurements to its data log. After
testing, retrieve the log from the roboRIO and open it in SysId. Select the
test-state entry and the matching motor position, speed, and voltage entries.
For more help, read the [WPILib System Identification guide](https://docs.wpilib.org/en/stable/docs/software/advanced-controls/system-identification/index.html).
