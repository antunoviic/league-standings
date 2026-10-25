from collections import Counter

from app.seed import CLUBS, ONGOING_ROUND, PLAYED_ROUNDS, build_demo_season, round_robin


def test_round_robin_pairs_every_club_twice():
    rounds = round_robin([c[0] for c in CLUBS])
    assert len(rounds) == 2 * (len(CLUBS) - 1)
    pairs = Counter(frozenset(match) for fixtures in rounds for match in fixtures)
    assert all(count == 2 for count in pairs.values())
    assert len(pairs) == len(CLUBS) * (len(CLUBS) - 1) // 2


def test_each_club_plays_once_per_round():
    for fixtures in round_robin([c[0] for c in CLUBS]):
        clubs = [club for match in fixtures for club in match]
        assert len(clubs) == len(set(clubs)) == len(CLUBS)


def test_standings_match_completed_results():
    data = build_demo_season()
    completed = [m for m in data["matches"] if m["match_status"] == "completed"]
    per_round = len(CLUBS) // 2

    assert len(completed) == PLAYED_ROUNDS * per_round
    assert sum(s["matches_played"] for s in data["standings"].values()) == 2 * len(completed)
    assert all(s["matches_played"] == PLAYED_ROUNDS for s in data["standings"].values())


def test_exactly_one_round_is_ongoing():
    data = build_demo_season()
    ongoing = [m for m in data["matches"] if m["match_status"] == "ongoing"]
    assert len(ongoing) == len(CLUBS) // 2
    assert ONGOING_ROUND == PLAYED_ROUNDS + 1


def test_seed_is_deterministic():
    assert build_demo_season() == build_demo_season()
