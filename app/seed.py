"""Deterministic demo data: one league, eight clubs and a double round-robin season.

The first rounds are already played (and counted in the standings), one round is
currently in progress and the rest is still scheduled.
"""

import random
from datetime import date, timedelta

from app.standings import result_deltas

LEAGUE = {"league_id": 1, "name": "Demo League", "country": "Austria"}
SEASON_YEAR = 2026
SEASON_START = date(2026, 8, 1)
SEASON_END = date(2027, 5, 31)
PLAYED_ROUNDS = 10
ONGOING_ROUND = PLAYED_ROUNDS + 1

CLUBS = [
    (1, "FC Donaustadt", "Vienna", "Donaupark Arena"),
    (2, "SV Murtal", "Graz", "Murtal Stadium"),
    (3, "Union Salzach", "Salzburg", "Salzach Park"),
    (4, "SK Innufer", "Innsbruck", "Alpenblick Arena"),
    (5, "ASK Traun", "Linz", "Traunstadion"),
    (6, "FC Wörthersee", "Klagenfurt", "Seeblick Arena"),
    (7, "SC Bodensee", "Bregenz", "Hafenstadion"),
    (8, "SV Leithaberg", "Eisenstadt", "Leitha Park"),
]


def round_robin(club_ids: list[int]) -> list[list[tuple[int, int]]]:
    """Circle-method schedule: every club plays every other club once at home and once away."""
    ids = list(club_ids)
    if len(ids) % 2:
        raise ValueError("Need an even number of clubs")
    rounds = []
    for r in range(len(ids) - 1):
        pairs = [(ids[i], ids[-1 - i]) for i in range(len(ids) // 2)]
        # alternate home advantage so no club is always at home
        rounds.append([(a, b) if (r + i) % 2 == 0 else (b, a) for i, (a, b) in enumerate(pairs)])
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]
    second_half = [[(away, home) for home, away in fixtures] for fixtures in rounds]
    return rounds + second_half


def build_demo_season(seed: int = 7) -> dict:
    """Generate matches and the matching standings without touching a database."""
    rng = random.Random(seed)
    standings = {club_id: {"matches_played": 0, "wins": 0, "draws": 0, "losses": 0, "points": 0}
                 for club_id, *_ in CLUBS}
    matches = []
    match_id = 1

    for round_no, fixtures in enumerate(round_robin([c[0] for c in CLUBS]), start=1):
        match_date = SEASON_START + timedelta(weeks=round_no - 1)
        for home_id, away_id in fixtures:
            if round_no <= ONGOING_ROUND:
                home_score, away_score = rng.randint(0, 4), rng.randint(0, 3)
            else:
                home_score, away_score = 0, 0

            if round_no <= PLAYED_ROUNDS:
                status = "completed"
                home_delta, away_delta = result_deltas(home_score, away_score)
                for club_id, delta in ((home_id, home_delta), (away_id, away_delta)):
                    row = standings[club_id]
                    for field in row:
                        row[field] += getattr(delta, field)
            elif round_no == ONGOING_ROUND:
                status = "ongoing"
            else:
                status = "scheduled"

            matches.append({
                "match_id": match_id,
                "season_year": SEASON_YEAR,
                "match_date": match_date,
                "home_club_id": home_id,
                "away_club_id": away_id,
                "home_score": home_score,
                "away_score": away_score,
                "match_status": status,
            })
            match_id += 1

    return {"matches": matches, "standings": standings}


def reset_demo_data(connection) -> dict:
    """Wipe all tables and load the demo season. Returns row counts per table."""
    data = build_demo_season()
    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in ("season_stat", "matches", "season", "club", "league"):
            cursor.execute(f"TRUNCATE TABLE {table}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        cursor.execute(
            "INSERT INTO league (league_id, name, country) VALUES (%s, %s, %s)",
            (LEAGUE["league_id"], LEAGUE["name"], LEAGUE["country"]),
        )
        cursor.executemany("INSERT INTO club (club_id, name, city, stadium_name) VALUES (%s, %s, %s, %s)", CLUBS)
        cursor.execute(
            "INSERT INTO season (season_year, start_date, end_date, league_id) VALUES (%s, %s, %s, %s)",
            (SEASON_YEAR, SEASON_START, SEASON_END, LEAGUE["league_id"]),
        )
        cursor.executemany(
            """
            INSERT INTO matches (match_id, season_year, match_date, home_club_id, away_club_id,
                                 home_score, away_score, match_status)
            VALUES (%(match_id)s, %(season_year)s, %(match_date)s, %(home_club_id)s, %(away_club_id)s,
                    %(home_score)s, %(away_score)s, %(match_status)s)
            """,
            data["matches"],
        )
        cursor.executemany(
            """
            INSERT INTO season_stat (season_year, club_id, matches_played, wins, draws, losses, points)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [(SEASON_YEAR, club_id, s["matches_played"], s["wins"], s["draws"], s["losses"], s["points"])
             for club_id, s in data["standings"].items()],
        )
    connection.commit()
    return {
        "league": 1,
        "club": len(CLUBS),
        "season": 1,
        "matches": len(data["matches"]),
        "season_stat": len(data["standings"]),
    }


if __name__ == "__main__":
    from app.db import get_mysql_connection

    conn = get_mysql_connection()
    try:
        print(reset_demo_data(conn))
    finally:
        conn.close()
