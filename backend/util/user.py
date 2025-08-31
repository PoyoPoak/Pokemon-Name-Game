"""Utility class for user management."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class User:
    """Minimal in‑memory user model."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.score = 0

    def add_score(self, delta: int = 1) -> int:
        """Increment score by `delta` (default 1) and return new value.

        Args:
            delta (int, optional): Amount to change score by. Defaults to 1.

        Returns:
            int: New score after addition.
        """
        if delta == 0:
            return self.score
        
        self.score += int(delta)
        
        if self.score < 0:
            self.score = 0
            
        return self.score

    def reset_score(self) -> None:
        """Reset score back to zero."""
        self.score = 0

        