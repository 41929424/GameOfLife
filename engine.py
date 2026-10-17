"""Pure-Python rules and state for Conway's Game of Life."""

from __future__ import annotations

import random

Field = list[list[bool]]


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

    def __init__(self, width: int, height: int | None = None, density: float = 0.28) -> None:
        height = width if height is None else height
        _validate_dimensions(width, height)
        self.width = width
        self.height = height
        self._field = make_field(width, height, density)
        self.generation = 0

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

    def step(self) -> None:
        self._field = next_generation(self._field)
        self.generation += 1

    def randomize(self, density: float = 0.28) -> None:
        self._field = make_field(self.width, self.height, density)
        self.generation = 0

    def clear(self) -> None:
        self._field = [[False] * self.width for _ in range(self.height)]
        self.generation = 0

    def resize(self, width: int, height: int) -> None:
        _validate_dimensions(width, height)
        resized = [[False] * width for _ in range(height)]
        for y in range(min(self.height, height)):
            for x in range(min(self.width, width)):
                resized[y][x] = self._field[y][x]
        self.width = width
        self.height = height
        self._field = resized
        self.generation = 0

    def set_cell(self, x: int, y: int, alive: bool) -> None:
        if (isinstance(x, bool) or not isinstance(x, int) or
                isinstance(y, bool) or not isinstance(y, int) or
                not (0 <= x < self.width and 0 <= y < self.height)):
            raise IndexError("cell coordinates are outside the field")
        alive = bool(alive)
        if self._field[y][x] != alive:
            self._field[y][x] = alive
            self.generation = 0
