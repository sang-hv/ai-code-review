from typing import Protocol


class ConventionsServiceProtocol(Protocol):
    def render(self, mode: str) -> str:
        """Return the conventions block for a review mode, or "" when disabled/empty."""
        ...
