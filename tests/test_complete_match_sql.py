"""Tests the SQL use case's transaction logic with a fake DB-API connection."""

import pytest

from app import create_app, db

MATCH = {
    "match_id": 10, "match_date": "2026-10-10", "home_score": 1, "away_score": 1,
    "match_status": "ongoing", "season_year": 2026,
    "home_club_id": 1, "away_club_id": 2, "home_club_name": "Home FC", "away_club_name": "Away SV",
}


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.statements.append((" ".join(sql.split()), params))
        if sql.lstrip().startswith("SELECT"):
            self._result = MATCH
        elif "UPDATE matches" in sql:
            self.rowcount = 1 if self.conn.match_is_ongoing else 0
            self.conn.match_is_ongoing = False
        else:
            self.rowcount = 1

    def fetchone(self):
        return self._result


class FakeConnection:
    def __init__(self, match_is_ongoing=True):
        self.match_is_ongoing = match_is_ongoing
        self.statements = []
        self.committed = self.rolled_back = self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def standing_updates(conn):
    return [params for sql, params in conn.statements if sql.startswith("UPDATE season_stat")]


def test_draw_updates_both_clubs_in_one_transaction(client, monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(db, "get_mysql_connection", lambda: conn)

    client.post("/complete-match", data={"match_id": 10})

    # (matches_played, wins, draws, losses, points, season, club)
    assert standing_updates(conn) == [(1, 0, 1, 0, 1, 2026, 1), (1, 0, 1, 0, 1, 2026, 2)]
    assert conn.committed and not conn.rolled_back and conn.closed


def test_match_that_is_no_longer_ongoing_is_not_counted(client, monkeypatch):
    conn = FakeConnection(match_is_ongoing=False)
    monkeypatch.setattr(db, "get_mysql_connection", lambda: conn)

    client.post("/complete-match", data={"match_id": 10})

    assert standing_updates(conn) == []
    assert conn.rolled_back and not conn.committed and conn.closed


def test_missing_match_id_does_not_touch_the_database(client, monkeypatch):
    monkeypatch.setattr(db, "get_mysql_connection", lambda: pytest.fail("should not connect"))

    response = client.post("/complete-match", data={})

    assert response.status_code == 302
