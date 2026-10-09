"""No-op pyfrc physics hook for logic-only simulation."""


class PhysicsEngine:
    """Satisfy pyfrc's physics interface without mechanism dynamics."""

    def __init__(self, physics_controller):
        """Store the native controller without modifying simulated state."""
        self.physics_controller = physics_controller

    def update_sim(self, now: float, tm_diff: float) -> None:
        """Perform no physics updates in this behavior-only proof."""
        pass
