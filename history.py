"""Bounded history for detecting repeated Game of Life states."""

from __future__ import annotations

from collections import deque

Field = list[list[bool]]
State = tuple[tuple[bool, ...], ...]


class StateHistory:
    """Store recent immutable field snapshots and report their repeat periods."""

    def __init__(self, limit: int = 1000) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        self._limit = limit
        self._states: deque[tuple[int, State]] = deque()
        self._latest_generation: dict[State, int] = {}
        self._last_generation: int | None = None

    @property
    def size(self) -> int:
        """Number of state appearances currently retained."""
        return len(self._states)

    def record(self, field: Field, generation: int) -> int | None:
        """Record a snapshot and return its period since its last retained appearance."""
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise ValueError("generation must be an integer")
        if self._last_generation is not None and generation <= self._last_generation:
            raise ValueError("generations must be recorded in strictly increasing order")

        if not field or not field[0]:
            raise ValueError("field must have at least one row and one column")
        width = len(field[0])
        if any(len(row) != width for row in field):
            raise ValueError("all field rows must have the same width")
        state: State = tuple(tuple(row) for row in field)

        previous_generation = self._latest_generation.get(state)
        period = (
            generation - previous_generation
            if previous_generation is not None
            else None
        )

        self._states.append((generation, state))
        self._latest_generation[state] = generation
        self._last_generation = generation

        if len(self._states) > self._limit:
            expired_generation, expired_state = self._states.popleft()
            if self._latest_generation.get(expired_state) == expired_generation:
                del self._latest_generation[expired_state]

        return period

    def clear(self) -> None:
        """Remove all recorded appearances and reset generation ordering."""
        self._states.clear()
        self._latest_generation.clear()
        self._last_generation = None
