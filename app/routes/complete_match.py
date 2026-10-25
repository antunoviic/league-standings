"""Use case "Complete Match" on MariaDB.

Marks an ongoing match as completed and updates both clubs' season standings
inside one transaction.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.standings import result_deltas

bp = Blueprint("complete_match", __name__)

MATCH_WITH_CLUBS = """
    SELECT m.match_id, m.match_date, m.home_score, m.away_score, m.match_status, m.season_year,
           m.home_club_id, m.away_club_id,
           hc.name AS home_club_name, ac.name AS away_club_name
    FROM matches m
    JOIN club hc ON hc.club_id = m.home_club_id
    JOIN club ac ON ac.club_id = m.away_club_id
"""

UPDATE_STANDING = """
    UPDATE season_stat
    SET matches_played = matches_played + %s,
        wins = wins + %s,
        draws = draws + %s,
        losses = losses + %s,
        points = points + %s
    WHERE season_year = %s AND club_id = %s
"""


@bp.get("/complete-match")
def complete_match_page():
    selected_match_id = request.args.get("match_id", type=int)
    selected_season_year = request.args.get("season_year", type=int)

    connection = db.get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(MATCH_WITH_CLUBS + " WHERE m.match_status = 'ongoing' ORDER BY m.match_date")
            matches = cursor.fetchall()

            selected_match = None
            if selected_match_id:
                cursor.execute(MATCH_WITH_CLUBS + " WHERE m.match_id = %s", (selected_match_id,))
                selected_match = cursor.fetchone()
                if selected_match and not selected_season_year:
                    selected_season_year = selected_match["season_year"]

            if not selected_season_year:
                cursor.execute("SELECT MAX(season_year) AS latest FROM season")
                row = cursor.fetchone()
                selected_season_year = row["latest"] if row else None

            standings = []
            if selected_season_year:
                cursor.execute(
                    """
                    SELECT c.name AS club_name, ss.matches_played, ss.wins, ss.draws, ss.losses, ss.points
                    FROM season_stat ss
                    JOIN club c ON c.club_id = ss.club_id
                    WHERE ss.season_year = %s
                    ORDER BY ss.points DESC, ss.wins DESC
                    """,
                    (selected_season_year,),
                )
                standings = cursor.fetchall()
    finally:
        connection.close()

    return render_template(
        "complete_match.html",
        matches=matches,
        selected_match_id=selected_match_id,
        selected_match=selected_match,
        standings=standings,
        selected_season_year=selected_season_year,
    )


@bp.post("/complete-match")
def complete_match_action():
    match_id = request.form.get("match_id", type=int)
    if not match_id:
        flash("No match selected.", "error")
        return redirect(url_for("complete_match.complete_match_page"))

    connection = db.get_mysql_connection()
    season_year = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(MATCH_WITH_CLUBS + " WHERE m.match_id = %s", (match_id,))
            match = cursor.fetchone()
            if not match:
                flash("Match not found.", "error")
                return redirect(url_for("complete_match.complete_match_page"))

            season_year = match["season_year"]

            # Conditional update: only one request can move the match from 'ongoing' to 'completed',
            # so a double click or two parallel requests cannot count the result twice.
            cursor.execute(
                "UPDATE matches SET match_status = 'completed' WHERE match_id = %s AND match_status = 'ongoing'",
                (match_id,),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                flash("This match is not ongoing and cannot be completed.", "error")
                return redirect(url_for("complete_match.complete_match_page", season_year=season_year))

            home, away = result_deltas(match["home_score"], match["away_score"])
            for club_id, delta in ((match["home_club_id"], home), (match["away_club_id"], away)):
                cursor.execute(
                    UPDATE_STANDING,
                    (delta.matches_played, delta.wins, delta.draws, delta.losses, delta.points,
                     season_year, club_id),
                )

        connection.commit()
        flash("Match completed. Season standings have been updated.", "success")
    except Exception as error:  # noqa: BLE001 - surface any DB error to the user
        connection.rollback()
        flash(f"Could not complete match: {error}", "error")
    finally:
        connection.close()

    return redirect(url_for("complete_match.complete_match_page", season_year=season_year))
