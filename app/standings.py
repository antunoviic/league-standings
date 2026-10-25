"""Pure league-table rules, shared by the SQL and the MongoDB implementation."""

from dataclasses import dataclass

POINTS_FOR_WIN = 3
POINTS_FOR_DRAW = 1


@dataclass(frozen=True)
class StandingDelta:
    """How one club's season row changes after a completed match."""

    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: int = 0
    matches_played: int = 1


def result_deltas(home_score: int, away_score: int) -> tuple[StandingDelta, StandingDelta]:
    """Return the (home, away) standing changes for a final score."""
    if home_score < 0 or away_score < 0:
        raise ValueError("Scores cannot be negative")

    if home_score > away_score:
        return StandingDelta(wins=1, points=POINTS_FOR_WIN), StandingDelta(losses=1)
    if away_score > home_score:
        return StandingDelta(losses=1), StandingDelta(wins=1, points=POINTS_FOR_WIN)
    draw = StandingDelta(draws=1, points=POINTS_FOR_DRAW)
    return draw, draw


def mongo_increment(home: StandingDelta, away: StandingDelta) -> dict:
    """Build the $inc document for the embedded standings array (array filters 'home' and 'away')."""
    inc = {}
    for alias, delta in (("home", home), ("away", away)):
        for field in ("matches_played", "wins", "draws", "losses", "points"):
            value = getattr(delta, field)
            if value:
                inc[f"standings.$[{alias}].{field}"] = value
    return {"$inc": inc}


def sort_standings(rows: list[dict]) -> list[dict]:
    """League order: points first, then wins."""
    return sorted(rows, key=lambda row: (-row["points"], -row["wins"]))
