import components
import magicbot


class DoNothing(magicbot.AutonomousStateMachine):

    MODE_NAME = "Do Nothing"
    DEFAULT = True

    # Injected from the definition in robot.py
    drivetrain: components.XRPTankDrive

    @magicbot.timed_state(duration=3, first=True)
    def do_nothing(self):
        self.drivetrain.stop()