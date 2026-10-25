import pytest

from app.standings import StandingDelta, mongo_increment, result_deltas, sort_standings


def test_home_win():
    home, away = result_deltas(2, 1)
    assert home == StandingDelta(wins=1, points=3)
    assert away == StandingDelta(losses=1)


def test_away_win():
    home, away = result_deltas(0, 3)
    assert home == StandingDelta(losses=1)
    assert away == StandingDelta(wins=1, points=3)


def test_draw_gives_both_clubs_one_point():
    home, away = result_deltas(1, 1)
    assert home == away == StandingDelta(draws=1, points=1)


def test_every_result_counts_as_a_played_match():
    for score in [(0, 0), (3, 0), (0, 2)]:
        assert all(d.matches_played == 1 for d in result_deltas(*score))


def test_negative_score_is_rejected():
    with pytest.raises(ValueError):
        result_deltas(-1, 0)


def test_mongo_increment_targets_both_array_filters():
    update = mongo_increment(*result_deltas(2, 0))
    assert update == {"$inc": {
        "standings.$[home].matches_played": 1,
        "standings.$[home].wins": 1,
        "standings.$[home].points": 3,
        "standings.$[away].matches_played": 1,
        "standings.$[away].losses": 1,
    }}


def test_sort_by_points_then_wins():
    rows = [
        {"club": "A", "points": 10, "wins": 2},
        {"club": "B", "points": 12, "wins": 3},
        {"club": "C", "points": 10, "wins": 3},
    ]
    assert [r["club"] for r in sort_standings(rows)] == ["B", "C", "A"]
