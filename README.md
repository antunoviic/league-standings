# League Standings

![CI](https://github.com/antunoviic/league-standings/actions/workflows/ci.yml/badge.svg)

A Flask web app that completes football matches and keeps the league table up to date, implemented twice: once on a **relational database (MariaDB)** and once on a **document database (MongoDB)**, with a migration that moves the data from one model to the other.

The point of the project is the comparison: the same use case, two data models, and the trade-offs each one brings.

## Tech stack

Python 3.12 · Flask · MariaDB (PyMySQL) · MongoDB (PyMongo) · pytest · Docker Compose · GitHub Actions

## The use case

"Complete Match": an ongoing match is marked as completed, and both clubs' season rows are updated (matches played, wins / draws / losses, points: 3 for a win, 1 for a draw).

The scoring rules live in one pure module ([`app/standings.py`](app/standings.py)) that both implementations share, so the table is calculated the same way regardless of the database.

## Relational vs. document model

| | MariaDB | MongoDB |
|---|---|---|
| Standings | own table `season_stat`, one row per club and season | array embedded in the season document |
| Reading the table | join `season_stat` ↔ `club` | single document read |
| Updating both clubs | two `UPDATE`s in one transaction | one `update_one` with positional array filters (`$[home]`, `$[away]`) |
| Match list | join to `club` for the names | club names denormalised into the match |
| Index | `(match_status, match_date)` | `(match_status, match_date)`, created by the migration |

### Guarding against double counting

Both versions move a match from `ongoing` to `completed` with a **conditional update** (`... WHERE match_status = 'ongoing'`). Only the first of two parallel requests can succeed, so a double click cannot count the same result twice.

### Known trade-off in the MongoDB version

The match status and the standings live in two different documents, so they are updated in two separate operations. MongoDB only guarantees atomicity per document without a multi-document transaction (which needs a replica set). If the second update failed, the match would be completed without its points. In the SQL version both changes are committed in one transaction. Moving to a replica set and wrapping both updates in a session transaction would close this gap.

## Running it

```bash
docker compose up --build
```

Then open http://localhost:5000 and follow the four steps on the start page:

1. Load demo data (one league, eight clubs, a season in progress)
2. Complete a match on MariaDB
3. Migrate SQL → MongoDB
4. Complete a match on MongoDB

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

- `test_standings.py`: scoring rules and the MongoDB update document
- `test_seed.py`: the round-robin schedule and that the demo standings match the played results
- `test_complete_match_sql.py`: transaction handling of the SQL version (commit, rollback, double completion) with a fake connection
- `test_complete_match_mongo.py`: end-to-end tests of the MongoDB version. They run against a real MongoDB when `MONGO_TEST_URI` is set, as in CI. Locally without it, the tests that need array filters are skipped because the in-memory mock does not support them.

## Project structure

```
app/
├── standings.py          scoring rules shared by both implementations
├── routes/
│   ├── complete_match.py         use case on MariaDB
│   └── complete_match_mongo.py   use case on MongoDB
├── migration.py          relational → document model
├── seed.py               deterministic demo season
└── db.py                 connection helpers
db/schema.sql             relational schema
```

## Background

This project grew out of a group assignment in a database systems course at the University of Vienna, in which I was responsible for the "Complete Match" use case and the SQL → MongoDB migration. This repository contains only my part, reworked into a standalone application; the schema, demo data, application setup and tests were written new for it.

## License

MIT
