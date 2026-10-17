import pytest

from history import StateHistory


STATE_A = [[False, True], [True, False]]
STATE_B = [[True, False], [False, True]]


def test_new_history_is_empty():
    assert StateHistory().size == 0


def test_first_state_has_no_repeat_period():
    history = StateHistory()
    assert history.record(STATE_A, 0) is None
    assert history.size == 1


def test_repeat_in_next_generation_has_period_one():
    history = StateHistory()
    assert history.record(STATE_A, 0) is None
    assert history.record(STATE_A, 1) == 1


def test_repeat_two_generations_later_has_period_two():
    history = StateHistory()
    history.record(STATE_A, 0)
    history.record(STATE_B, 1)
    assert history.record(STATE_A, 2) == 2


def test_repeated_cycle_period_uses_last_appearance():
    history = StateHistory()
    assert history.record(STATE_A, 0) is None
    assert history.record(STATE_B, 1) is None
    assert history.record(STATE_A, 2) == 2
    assert history.record(STATE_B, 3) == 2
    assert history.record(STATE_A, 4) == 2


def test_history_size_is_bounded_and_oldest_appearance_is_removed():
    history = StateHistory(limit=2)
    history.record(STATE_A, 0)
    history.record(STATE_B, 1)
    assert history.record([[True, True], [False, False]], 2) is None
    assert history.size == 2
    assert history.record(STATE_A, 3) is None


def test_eviction_preserves_latest_mapping_for_repeated_state():
    history = StateHistory(limit=2)
    history.record(STATE_A, 0)
    history.record(STATE_B, 1)
    assert history.record(STATE_A, 2) == 2
    # Evict the earlier A appearance while its newer appearance remains stored.
    assert history.record(STATE_B, 3) == 2
    assert history.record(STATE_A, 4) == 2
    assert history.record(STATE_B, 5) == 2


def test_eviction_removes_a_state_when_its_latest_appearance_expires():
    history = StateHistory(limit=2)
    history.record(STATE_A, 0)
    history.record(STATE_B, 1)
    history.record(STATE_A, 2)
    history.record([[True, True], [False, False]], 3)
    assert history.record(STATE_B, 4) is None


def test_clear_removes_history_and_resets_generation_order():
    history = StateHistory()
    history.record(STATE_A, 10)
    history.clear()
    assert history.size == 0
    assert history.record(STATE_A, 0) is None


def test_history_is_independent_from_later_field_mutation():
    history = StateHistory()
    field = [[False, True], [True, False]]
    history.record(field, 0)
    field[0][0] = True
    assert history.record(STATE_A, 1) == 1


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_limit_is_rejected(limit):
    with pytest.raises(ValueError):
        StateHistory(limit=limit)


def test_non_increasing_generation_is_rejected():
    history = StateHistory()
    history.record(STATE_A, 3)
    with pytest.raises(ValueError, match="strictly increasing"):
        history.record(STATE_B, 3)
    with pytest.raises(ValueError, match="strictly increasing"):
        history.record(STATE_B, 2)
    assert history.size == 1
    assert history.record(STATE_B, 4) is None
