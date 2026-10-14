"""XRP MagicBot."""
# To Run: robotpy sim --xrp

import os

import components
import constants
import magicbot
import wpilib
import xrp

os.environ["HALSIMXRP_HOST"] = "192.168.42.1"
os.environ["HALSIMXRP_PORT"] = "3540"


class MyRobot(magicbot.MagicRobot):
    """Define the robot."""

    # Magicbot components
    controller: components.XboxController
    drivetrain: components.XRPTankDrive
    led: components.XRPLed
    servo: components.XRPServo
    rangefinder: components.XRPRangefinder
    reflectance_sensor: components.XRPReflectanceSensor

    def createObjects(self) -> None:
        """Construct RobotPy objects before MagicBot injects the component."""
        # Create the hardware objects
        hardware = {
            "led": xrp.XRPOnBoardIO(),
            "servo": xrp.XRPServo(constants.Ids.SERVO),
            "rangefinder": xrp.XRPRangefinder(),
            "reflectance_sensor": xrp.XRPReflectanceSensor(),
            "left_motor": xrp.XRPMotor(constants.Ids.LEFT_MOTOR),
            "right_motor": xrp.XRPMotor(constants.Ids.RIGHT_MOTOR),
            "left_encoder": wpilib.Encoder(*constants.Ids.LEFT_ENCODER),
            "right_encoder": wpilib.Encoder(*constants.Ids.RIGHT_ENCODER),
        }

        if constants.LOGGING_ENABLED:
            wpilib.DataLogManager.start()
            self.log = wpilib.DataLogManager.getLog()

        self.controller_port = constants.Ids.CONTROLLER

        # Setup the drivetrain
        ## Create motor objects
        left_motor = hardware["left_motor"]
        left_motor.setSafetyEnabled(True)
        right_motor = hardware["right_motor"]
        right_motor.setSafetyEnabled(True)
        right_motor.setInverted(True)
        ## Create the encoder objects
        right_encoder = hardware["right_encoder"]
        left_encoder = hardware["left_encoder"]
        right_encoder.setDistancePerPulse(constants.Robot.DISTANCE_PER_PULSE)
        right_encoder.setReverseDirection(True)
        left_encoder.setDistancePerPulse(constants.Robot.DISTANCE_PER_PULSE)
        ## Inject objects and parameters
        self.drivetrain_gyro = xrp.XRPGyro()
        self.drivetrain_gyro_noise_threshold = constants.Robot.GYRO_NOISE_THRESHOLD
        self.drivetrain_left_motor = left_motor
        self.drivetrain_right_motor = right_motor
        self.drivetrain_left_encoder = left_encoder
        self.drivetrain_right_encoder = right_encoder

        # Set up the LED
        self.led_the_led = hardware["led"]
        self.led_blink_time = constants.LED_BLINK_TIME

        # Set up the servo
        self.servo_the_servo = hardware["servo"]
        self.servo_change = constants.Robot.SERVO_CHANGE

        # Set up the rangefinder
        self.rangefinder_sensor = hardware["rangefinder"]

        # Set up the reflectance sensor
        self.reflectance_sensor_sensor = hardware["reflectance_sensor"]

    def autonomousInit(self):
        """Initialize autonomous mode."""
        self.led.mode = "on"

    def disabledPeriodic(self):
        """Run during disabled mode."""
        self.led.mode = "off"
        self.drivetrain.stop()

    def teleopInit(self):
        """Initialize teleop mode."""
        self.led.mode = "blink"

    def teleopPeriodic(self):
        """Run during teleop mode."""
        # Pass in the speed and let the drivetrain component handle the rest
        self.drivetrain.throttle = -self.controller.left_y
        self.drivetrain.rotation = -self.controller.right_x

        # Servo control with bumpers
        ## Left bumper raises the servo, right bumper lowers it
        if self.controller.left_bumper_pressed():
            self.servo.position += self.servo_change
        elif self.controller.right_bumper_pressed():
            self.servo.position -= self.servo_change

    @magicbot.feedback
    def pose(self):
        """Return the robot's pose as a list of [x, y, rotation]."""
        return [
            self.drivetrain.pose.X(),
            self.drivetrain.pose.Y(),
            self.drivetrain.pose.rotation().degrees(),
        ]

    @magicbot.feedback
    def servo_position(self) -> float:
        """Return the servo's position."""
        return self.servo.position

    @magicbot.feedback
    def rangefinder_distance(self) -> float:
        """Return the rangefinder's distance in the specified unit."""
        return self.rangefinder.distance

    @magicbot.feedback
    def rangefinder_units(self) -> str:
        """Return the rangefinder's distance units."""
        return self.rangefinder.unit

    @magicbot.feedback
    def line_detected(self) -> list[bool]:
        """Return if a line is detected as a list of [left, right]."""
        return [
            self.reflectance_sensor.line_on_left,
            self.reflectance_sensor.line_on_right,
        ]
