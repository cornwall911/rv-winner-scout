"""Global run deadline coordinator."""

import time
from rv_winner_scout.domain.exceptions import DeadlineExceededError


class DeadlineManager:
    """Monitors run execution lifespan against global deadline."""

    def __init__(self, deadline_minutes: int = 45, halt_threshold_minutes: int = 5) -> None:
        self.deadline_seconds = deadline_minutes * 60.0
        self.halt_threshold_seconds = halt_threshold_minutes * 60.0
        self.start_time = time.time()

    def remaining_seconds(self) -> float:
        elapsed = time.time() - self.start_time
        return max(0.0, self.deadline_seconds - elapsed)

    def should_halt_discovery(self) -> bool:
        """Returns True if remaining time is under the cutoff threshold to allow clean flush."""
        return self.remaining_seconds() <= self.halt_threshold_seconds

    def check_deadline(self) -> None:
        """Raises DeadlineExceededError if the global deadline has been exceeded."""
        if self.remaining_seconds() <= 0.0:
            raise DeadlineExceededError("Global run execution deadline exceeded.")
