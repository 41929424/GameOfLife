"""Pure-Python rules and state for Conway's Game of Life."""

from __future__ import annotations

import random
from typing import Literal

from history import StateHistory

Field = list[list[bool]]
AnalysisStatus = Literal["evolving", "stable", "oscillating"]


def _validate_dimensions(width: int, height: int) -> None:
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be a positive integer")
    if isinstance(height, bool) or not isinstance(height, int) or height < 1:
        raise ValueError("height must be a positive integer")


def make_field(width: int, height: int | None = None, density: float = 0.28) -> Field:
    """Create a random field of the requested size and live-cell density."""
    height = width if height is None else height
    _validate_dimensions(width, height)
    if isinstance(density, bool) or not isinstance(density, (int, float)) or not 0 <= density <= 1:
        raise ValueError("density must be between 0 and 1")
    return [[random.random() < density for _ in range(width)] for _ in range(height)]


def next_generation(field: Field) -> Field:
    """Calculate one generation. Cells beyond the field edges are dead."""
    if not field or not field[0]:
        raise ValueError("field must have at least one row and one column")
    rows, cols = len(field), len(field[0])
    if any(len(row) != cols for row in field):
        raise ValueError("all field rows must have the same width")

    result = [[False] * cols for _ in range(rows)]
    for y in range(rows):
        for x in range(cols):
            neighbors = sum(
                field[row][col]
                for row in range(max(0, y - 1), min(rows, y + 2))
                for col in range(max(0, x - 1), min(cols, x + 2))
                if (row, col) != (y, x)
            )
            result[y][x] = neighbors == 3 or (field[y][x] and neighbors == 2)
    return result


class GameEngine:
    """Own the game field and generation counter, without UI dependencies."""

    def __init__(
        self,
        width: int,
        height: int | None = None,
        density: float = 0.28,
        history_limit: int = 1000,
    ) -> None:
        height = width if height is None else height
        _validate_dimensions(width, height)
        self.width = width
        self.height = height
        self._field = make_field(width, height, density)
        self.generation = 0
        self._history = StateHistory(history_limit)
        self._status: AnalysisStatus = "evolving"
        self._cycle_period: int | None = None
        self._cycle_start: int | None = None
        self._history.record(self._field, self.generation)

    def get_field(self) -> Field:
        """Return a copy so callers cannot mutate the engine's internal state."""
        return [row[:] for row in self._field]

    @property
    def population(self) -> int:
        return sum(sum(row) for row in self._field)

    @property
    def density(self) -> float:
        return self.population / (self.width * self.height)

    @property
    def is_empty(self) -> bool:
        return self.population == 0

    @property
    def status(self) -> AnalysisStatus:
        return self._status

    @property
    def cycle_period(self) -> int | None:
        return self._cycle_period

    @property
    def cycle_start(self) -> int | None:
        return self._cycle_start

    @property
    def history_size(self) -> int:
        return self._history.size

    def _reset_history(self) -> None:
        self._history.clear()
        self.generation = 0
        self._status = "evolving"
        self._cycle_period = None
        self._cycle_start = None
        self._history.record(self._field, self.generation)

    def step(self) -> None:
        self._field = next_generation(self._field)
        self.generation += 1
        period = self._history.record(self._field, self.generation)
        if period is None:
            self._status = "evolving"
            self._cycle_period = None
            self._cycle_start = None
        else:
            self._status = "stable" if period == 1 else "oscillating"
            self._cycle_period = period
            self._cycle_start = self.generation - period

    def randomize(self, density: float = 0.28) -> None:
        self._field = make_field(self.width, self.height, density)
        self._reset_history()

    def clear(self) -> None:
        self._field = [[False] * self.width for _ in range(self.height)]
        self._reset_history()

    def resize(self, width: int, height: int) -> None:
        _validate_dimensions(width, height)
        resized = [[False] * width for _ in range(height)]
        for y in range(min(self.height, height)):
            for x in range(min(self.width, width)):
                resized[y][x] = self._field[y][x]
        self.width = width
        self.height = height
        self._field = resized
        self._reset_history()

    def set_cell(self, x: int, y: int, alive: bool) -> None:
        if (isinstance(x, bool) or not isinstance(x, int) or
                isinstance(y, bool) or not isinstance(y, int) or
                not (0 <= x < self.width and 0 <= y < self.height)):
            raise IndexError("cell coordinates are outside the field")
        alive = bool(alive)
        if self._field[y][x] != alive:
            self._field[y][x] = alive
            self._reset_history()
