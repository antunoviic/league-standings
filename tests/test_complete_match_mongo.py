"""End-to-end tests of the MongoDB use case.

Runs against a real MongoDB when MONGO_TEST_URI is set (as in CI). Without it, an in-memory
mongomock database is used; mongomock does not implement array filters, so the tests that
update standings are skipped in that case.
"""

import os

import mongomock
import pytest
from pymongo import MongoClient

from app import create_app, db

MONGO_TEST_URI = os.getenv("MONGO_TEST_URI")
needs_real_mongo = pytest.mark.skipif(
    not MONGO_TEST_URI, reason="array filters need a real MongoDB (set MONGO_TEST_URI)"
)


@pytest.fixture
def mongo(monkeypatch):
    if MONGO_TEST_URI:
        client = MongoClient(MONGO_TEST_URI)
        client.drop_database("league_test")
        database = client["league_test"]
    else:
        database = mongomock.MongoClient()["league"]
    database.seasons.insert_one({
        "_id": 2026,
        "league": {"league_id": 1, "name": "Demo League", "country": "Austria"},
        "standings": [
            {"club_id": 1, "club_name": "Home FC", "matches_played": 0, "wins": 0, "draws": 0, "losses": 0, "points": 0},
            {"club_id": 2, "club_name": "Away SV", "matches_played": 0, "wins": 0, "draws": 0, "losses": 0, "points": 0},
        ],
    })
    database.matches.insert_one({
        "_id": 10, "season_year": 2026, "match_date": "2026-10-10", "match_status": "ongoing",
        "home_club_id": 1, "home_club_name": "Home FC", "home_score": 2,
        "away_club_id": 2, "away_club_name": "Away SV", "away_score": 1,
    })
    monkeypatch.setattr(db, "get_mongo_database", lambda: database)
    return database


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def standing(mongo, club_id):
    season = mongo.seasons.find_one({"_id": 2026})
    return next(row for row in season["standings"] if row["club_id"] == club_id)


@needs_real_mongo
def test_completing_a_match_updates_both_clubs(client, mongo):
    response = client.post("/complete-match-mongo", data={"match_id": 10})

    assert response.status_code == 302
    assert mongo.matches.find_one({"_id": 10})["match_status"] == "completed"
    home = standing(mongo, 1)
    assert (home["matches_played"], home["wins"], home["points"]) == (1, 1, 3)
    assert standing(mongo, 2)["losses"] == 1
    assert standing(mongo, 2)["points"] == 0


@needs_real_mongo
def test_a_match_cannot_be_counted_twice(client, mongo):
    client.post("/complete-match-mongo", data={"match_id": 10})
    client.post("/complete-match-mongo", data={"match_id": 10})

    assert standing(mongo, 1)["matches_played"] == 1
    assert standing(mongo, 1)["points"] == 3


def test_page_lists_ongoing_matches_and_table(client, mongo):
    page = client.get("/complete-match-mongo").get_data(as_text=True)

    assert "Home FC" in page and "Away SV" in page
    assert "Season 2026 Standings" in page


def test_unknown_match_changes_nothing(client, mongo):
    client.post("/complete-match-mongo", data={"match_id": 999})

    assert mongo.matches.find_one({"_id": 10})["match_status"] == "ongoing"
    assert standing(mongo, 1)["matches_played"] == 0
