import pytest

from engine import GameEngine, make_field, next_generation


def test_creation_and_random_field_dimensions():
    engine = GameEngine(4, 2, density=0)
    assert (engine.width, engine.height, engine.generation) == (4, 2, 0)
    assert engine.get_field() == [[False] * 4 for _ in range(2)]
    assert make_field(3, density=1) == [[True] * 3 for _ in range(3)]


def make_block_engine(history_limit=1000):
    engine = GameEngine(4, 4, density=0, history_limit=history_limit)
    for x, y in ((1, 1), (2, 1), (1, 2), (2, 2)):
        engine.set_cell(x, y, True)
    return engine


def test_analysis_starts_evolving_with_initial_state_in_history():
    engine = GameEngine(4, 4, density=0)
    assert engine.status == "evolving"
    assert engine.cycle_period is None
    assert engine.cycle_start is None
    assert engine.history_size == 1


def test_block_is_stable_with_period_one_and_correct_cycle_start():
    engine = make_block_engine()
    engine.step()
    assert engine.status == "stable"
    assert engine.cycle_period == 1
    assert engine.cycle_start == 0


def test_blinker_is_oscillating_with_period_two():
    engine = GameEngine(5, 5, density=0)
    for x in (1, 2, 3):
        engine.set_cell(x, 2, True)
    engine.step()
    assert engine.status == "evolving"
    engine.step()
    assert engine.status == "oscillating"
    assert engine.cycle_period == 2
    assert engine.cycle_start == 0


def test_empty_field_is_stable():
    engine = GameEngine(3, 3, density=0)
    engine.step()
    assert engine.status == "stable"
    assert engine.cycle_period == 1
    assert engine.cycle_start == 0


def test_analysis_continues_after_cycle_and_updates_cycle_start():
    engine = make_block_engine()
    engine.step()
    engine.step()
    assert (engine.status, engine.cycle_period, engine.cycle_start) == ("stable", 1, 1)
    assert engine.generation == 2
    assert engine.history_size == 3


def test_history_limit_can_hide_a_longer_cycle():
    engine = GameEngine(5, 5, density=0, history_limit=1)
    for x in (1, 2, 3):
        engine.set_cell(x, 2, True)
    engine.step()
    engine.step()
    assert engine.history_size == 1
    assert engine.status == "evolving"
    assert engine.cycle_period is None
    assert engine.cycle_start is None


@pytest.mark.parametrize("operation", ["randomize", "clear", "resize", "set_cell"])
def test_configuration_changes_reset_analysis_and_register_generation_zero(operation):
    engine = make_block_engine()
    engine.step()
    assert engine.status == "stable"

    if operation == "randomize":
        engine.randomize(density=0)
    elif operation == "clear":
        engine.clear()
    elif operation == "resize":
        engine.resize(5, 5)
    else:
        engine.set_cell(1, 1, False)

    assert engine.generation == 0
    assert engine.status == "evolving"
    assert engine.cycle_period is None
    assert engine.cycle_start is None
    assert engine.history_size == 1


def test_setting_existing_cell_value_does_not_reset_analysis():
    engine = make_block_engine()
    engine.step()
    engine.set_cell(1, 1, True)
    assert engine.generation == 1
    assert engine.status == "stable"
    assert engine.cycle_period == 1
    assert engine.cycle_start == 0
    assert engine.history_size == 2


def test_analysis_properties_are_read_only():
    engine = GameEngine(2, 2, density=0)
    with pytest.raises(AttributeError):
        engine.status = "stable"
    with pytest.raises(AttributeError):
        engine.cycle_period = 1
    with pytest.raises(AttributeError):
        engine.cycle_start = 0
    with pytest.raises(AttributeError):
        engine.history_size = 1


@pytest.mark.parametrize("width,height", [(0, 2), (2, 0), (-1, 2), (2, 1.5)])
def test_invalid_dimensions_are_rejected(width, height):
    with pytest.raises(ValueError):
        GameEngine(width, height, density=0)


def test_next_generation_obeys_conway_rules_and_dead_boundaries():
    field = [
        [False] * 5,
        [False] * 5,
        [False, True, True, True, False],
        [False] * 5,
        [False] * 5,
    ]
    expected = [
        [False] * 5,
        [False, False, True, False, False],
        [False, False, True, False, False],
        [False, False, True, False, False],
        [False] * 5,
    ]
    assert next_generation(field) == expected
    assert next_generation([[True]]) == [[False]]


def test_step_advances_field_and_generation():
    engine = GameEngine(5, 5, density=0)
    for x in (1, 2, 3):
        engine.set_cell(x, 2, True)
    engine.step()
    assert engine.generation == 1
    assert engine.get_field()[1:4] == [
        [False, False, True, False, False],
        [False, False, True, False, False],
        [False, False, True, False, False],
    ]


def test_clear_and_randomize_reset_generation():
    engine = GameEngine(4, 2, density=0)
    engine.set_cell(0, 0, True)
    engine.step()
    engine.clear()
    assert engine.get_field() == [[False] * 4 for _ in range(2)]
    assert engine.is_empty and engine.population == 0 and engine.generation == 0
    engine.randomize(density=1)
    assert engine.get_field() == [[True] * 4 for _ in range(2)]
    assert engine.population == 8 and engine.density == 1
    assert engine.generation == 0


def test_resize_preserves_cells_when_growing_and_resets_generation():
    engine = GameEngine(4, 4, density=0)
    for x, y in ((1, 1), (2, 1), (1, 2), (2, 2)):
        engine.set_cell(x, y, True)
    engine.step()
    engine.resize(5, 6)
    assert (engine.width, engine.height, engine.generation) == (5, 6, 0)
    assert engine.get_field()[1][1:3] == [True, True]
    assert engine.get_field()[2][1:3] == [True, True]
    assert engine.population == 4
    assert engine.get_field()[5] == [False] * 5


def test_resize_discards_cells_outside_smaller_field():
    engine = GameEngine(5, 4, density=0)
    engine.set_cell(1, 1, True)
    engine.set_cell(4, 3, True)
    engine.resize(3, 2)
    assert engine.get_field() == [
        [False, False, False],
        [False, True, False],
    ]


def test_get_field_returns_independent_copy():
    engine = GameEngine(2, 2, density=0)
    exposed = engine.get_field()
    exposed[0][0] = True
    exposed.append([True, True])
    assert engine.get_field() == [[False, False], [False, False]]


@pytest.mark.parametrize("x,y", [(-1, 0), (0, -1), (3, 0), (0, 3), (1.2, 0), (True, 1)])
def test_set_cell_rejects_invalid_coordinates(x, y):
    engine = GameEngine(3, 3, density=0)
    with pytest.raises(IndexError):
        engine.set_cell(x, y, True)


def test_manual_cell_change_resets_generation():
    engine = GameEngine(5, 5, density=1)
    engine.step()
    assert engine.generation == 1
    engine.set_cell(0, 0, False)
    assert engine.generation == 0
