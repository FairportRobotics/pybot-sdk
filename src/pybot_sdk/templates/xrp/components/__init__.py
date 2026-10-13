"""Allow for importing components in robot.py with less typing."""

# Import all the components that you want to use here
from .xboxcontroller import XboxController
from .xrpled import XRPLed
from .xrprangefinder import XRPRangefinder
from .xrpreflectancesensor import XRPReflectanceSensor
from .xrpservo import XRPServo

# This list is used to determine what is imported when using `from components import *`
__all__ = [
    "XboxController",
    "XRPLed",
    "XRPRangefinder",
    "XRPReflectanceSensor",
    "XRPServo"
]