# XRP MagicBot
# To Run: robotpy sim --xrp

import components
import constants
import magicbot
import os
import wpilib
import xrp

os.environ["HALSIMXRP_HOST"] = "192.168.42.1"
os.environ["HALSIMXRP_PORT"] = "3540"


class MyRobot(magicbot.MagicRobot):
    # Magicbot components
    controller: components.XboxController
    drivetrain: components.XRPTankDrive
    led: components.XRPLed
    servo: components.XRPServo
    rangefinder: components.XRPRangefinder
    reflectance_sensor: components.XRPReflectanceSensor

    def createObjects(self):
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
        self.led.mode = "on"

    def disabledPeriodic(self):
        self.led.mode = "off"
        self.drivetrain.stop()

    def teleopInit(self):
        self.led.mode = "blink"

    def teleopPeriodic(self):
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
        return [
            0.0,  # self.localizer.pose.X,
            0.0,  # self.localizer.pose.Y,
            self.drivetrain.angle,
        ]