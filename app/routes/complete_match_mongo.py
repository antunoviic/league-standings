"""Use case "Complete Match" on MongoDB.

Standings are embedded in the season document, so each club's row is updated in place
with positional array filters.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.standings import mongo_increment, result_deltas, sort_standings

bp = Blueprint("complete_match_mongo", __name__)


def _with_match_id(match):
    """The match id is stored as _id; templates expect match_id."""
    if match:
        match["match_id"] = match["_id"]
    return match


@bp.get("/complete-match-mongo")
def complete_match_mongo_page():
    selected_match_id = request.args.get("match_id", type=int)
    selected_season_year = request.args.get("season_year", type=int)
    mongo = db.get_mongo_database()

    # served by the index on match_status created during migration
    matches = [_with_match_id(m) for m in mongo.matches.find({"match_status": "ongoing"}).sort("match_date", 1)]

    selected_match = None
    if selected_match_id:
        selected_match = _with_match_id(mongo.matches.find_one({"_id": selected_match_id}))
        if selected_match and not selected_season_year:
            selected_season_year = selected_match["season_year"]

    if not selected_season_year:
        latest = mongo.seasons.find_one({}, sort=[("_id", -1)])
        selected_season_year = latest["_id"] if latest else None

    standings, league_name = [], None
    if selected_season_year:
        season = mongo.seasons.find_one({"_id": selected_season_year})
        if season:
            standings = sort_standings(season.get("standings", []))
            league_name = season.get("league", {}).get("name")

    return render_template(
        "complete_match_mongo.html",
        matches=matches,
        selected_match_id=selected_match_id,
        selected_match=selected_match,
        standings=standings,
        selected_season_year=selected_season_year,
        league_name=league_name,
    )


@bp.post("/complete-match-mongo")
def complete_match_mongo_action():
    match_id = request.form.get("match_id", type=int)
    if not match_id:
        flash("No match selected.", "error")
        return redirect(url_for("complete_match_mongo.complete_match_mongo_page"))

    mongo = db.get_mongo_database()
    season_year = None
    try:
        match = mongo.matches.find_one({"_id": match_id})
        if not match:
            flash("Match not found.", "error")
            return redirect(url_for("complete_match_mongo.complete_match_mongo_page"))

        season_year = match["season_year"]

        # Atomic status transition on the match document guards against counting a result twice.
        transition = mongo.matches.update_one(
            {"_id": match_id, "match_status": "ongoing"},
            {"$set": {"match_status": "completed"}},
        )
        if transition.modified_count != 1:
            flash("This match is not ongoing and cannot be completed.", "error")
            return redirect(url_for("complete_match_mongo.complete_match_mongo_page", season_year=season_year))

        home, away = result_deltas(match["home_score"], match["away_score"])
        mongo.seasons.update_one(
            {"_id": season_year},
            mongo_increment(home, away),
            array_filters=[
                {"home.club_id": match["home_club_id"]},
                {"away.club_id": match["away_club_id"]},
            ],
        )
        flash("Match completed. Season standings have been updated.", "success")
    except Exception as error:  # noqa: BLE001
        flash(f"Could not complete match: {error}", "error")

    return redirect(url_for("complete_match_mongo.complete_match_mongo_page", season_year=season_year))
