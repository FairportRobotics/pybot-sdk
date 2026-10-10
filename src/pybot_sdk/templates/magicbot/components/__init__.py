"""Allow for importing components in robot.py with less typing."""

# Import all the components that you want to use here
from .controller import XboxController

# This list is used to determine what is imported when using `from components import *`
__all__ = [
    "XboxController",
]