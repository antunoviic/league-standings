"""Migrates the relational data into a document model.

Design of the document model:
- clubs:   one document per club
- seasons: league embedded, standings embedded as an array (read together on every table view)
- matches: club names denormalised into the match so the match list needs no lookups
"""

from pymongo import ASCENDING


def migrate_sql_to_mongo(sql_connection, mongo) -> dict:
    """Replace the MongoDB collections with the current relational data. Returns document counts."""
    with sql_connection.cursor() as cursor:
        cursor.execute("SELECT club_id, name, city, stadium_name FROM club")
        clubs = [
            {"_id": row["club_id"], "name": row["name"], "city": row["city"], "stadium_name": row["stadium_name"]}
            for row in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT ss.season_year, ss.club_id, c.name AS club_name,
                   ss.matches_played, ss.wins, ss.draws, ss.losses, ss.points
            FROM season_stat ss
            JOIN club c ON c.club_id = ss.club_id
            ORDER BY ss.points DESC, ss.wins DESC
            """
        )
        standings_by_season = {}
        for row in cursor.fetchall():
            standings_by_season.setdefault(row["season_year"], []).append({
                "club_id": row["club_id"],
                "club_name": row["club_name"],
                "matches_played": row["matches_played"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
                "points": row["points"],
            })

        cursor.execute(
            """
            SELECT s.season_year, s.start_date, s.end_date, l.league_id, l.name AS league_name, l.country
            FROM season s
            JOIN league l ON l.league_id = s.league_id
            """
        )
        seasons = [
            {
                "_id": row["season_year"],
                "start_date": str(row["start_date"]),
                "end_date": str(row["end_date"]),
                "league": {"league_id": row["league_id"], "name": row["league_name"], "country": row["country"]},
                "standings": standings_by_season.get(row["season_year"], []),
            }
            for row in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT m.match_id, m.match_date, m.match_status, m.home_score, m.away_score, m.season_year,
                   m.home_club_id, hc.name AS home_club_name, m.away_club_id, ac.name AS away_club_name
            FROM matches m
            JOIN club hc ON hc.club_id = m.home_club_id
            JOIN club ac ON ac.club_id = m.away_club_id
            """
        )
        matches = [
            {
                "_id": row["match_id"],
                "match_date": str(row["match_date"]),
                "match_status": row["match_status"],
                "home_score": row["home_score"],
                "away_score": row["away_score"],
                "season_year": row["season_year"],
                "home_club_id": row["home_club_id"],
                "home_club_name": row["home_club_name"],
                "away_club_id": row["away_club_id"],
                "away_club_name": row["away_club_name"],
            }
            for row in cursor.fetchall()
        ]

    for name in ("clubs", "seasons", "matches"):
        mongo[name].drop()

    if clubs:
        mongo.clubs.insert_many(clubs)
    if seasons:
        mongo.seasons.insert_many(seasons)
    if matches:
        mongo.matches.insert_many(matches)

    # the Complete Match page lists ongoing matches by date
    mongo.matches.create_index([("match_status", ASCENDING), ("match_date", ASCENDING)], name="idx_status_date")

    return {"clubs": len(clubs), "seasons": len(seasons), "matches": len(matches)}
