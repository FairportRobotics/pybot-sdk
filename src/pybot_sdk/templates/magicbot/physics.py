"""No-op pyfrc physics hook for logic-only simulation."""


class PhysicsEngine:
    """Satisfy pyfrc's physics interface without modeling mechanism dynamics."""

    def __init__(self, physics_controller):
        """Keep the native pyfrc controller available for future models."""
        self.physics_controller = physics_controller

    def update_sim(self, now: float, tm_diff: float) -> None:
        """Advance no physics; tests observe commanded outputs only."""
        pass
