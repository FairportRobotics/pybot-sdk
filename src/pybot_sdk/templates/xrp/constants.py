"""Constants for the robot."""

import math

LED_BLINK_TIME = 0.25
LOGGING_ENABLED = False


class Ids:
    """Constants for channels and ports."""

    LEFT_MOTOR = 0
    RIGHT_MOTOR = 1
    LEFT_ENCODER = (4, 5)
    RIGHT_ENCODER = (6, 7)
    SERVO = 4
    CONTROLLER = 0


class Robot:
    """Robot specific constants."""

    PULSES_PER_REVOLUTION = 12.0
    TICKS_PER_REV = 585.0
    GEAR_RATIO = (30.0 / 14.0) * (28.0 / 16.0) * (36.0 / 9.0) * (26.0 / 8.0)  # 48.75:1
    WHEEL_DIAMETER_MM = 60.0
    WHEEL_DIAMETER_M = WHEEL_DIAMETER_MM / 1000.0
    TRACK_WIDTH_INCHES = 6.0
    GYRO_NOISE_THRESHOLD = 0.025
    SERVO_CHANGE = 0.025
    DEFAULT_DRIVETRAIN_CONTROL_STYLE = "arcade"
    DISTANCE_PER_PULSE = (
        math.pi * WHEEL_DIAMETER_M / (PULSES_PER_REVOLUTION * GEAR_RATIO)
    )
