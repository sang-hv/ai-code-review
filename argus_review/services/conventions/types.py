from typing import Protocol


class ConventionsServiceProtocol(Protocol):
    def render(self, mode: str) -> str:
        """Return the conventions block for a review mode, or "" when disabled/empty."""
        ...

    def materialize(self, mode: str | None = None) -> str:
        """
        Write resolved convention docs to disk and return a lightweight inventory
        (path + line count) for the agent to search, or "" when disabled/empty.
        """
        ...
