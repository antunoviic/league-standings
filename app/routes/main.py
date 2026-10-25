from flask import Blueprint, flash, jsonify, redirect, render_template, url_for

from app import db
from app.migration import migrate_sql_to_mongo
from app.seed import reset_demo_data

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.post("/reset-data")
def reset_data():
    connection = db.get_mysql_connection()
    try:
        counts = reset_demo_data(connection)
        flash(f"Demo data loaded: {counts['club']} clubs, {counts['matches']} matches.", "success")
    except Exception as error:  # noqa: BLE001
        connection.rollback()
        flash(f"Could not load demo data: {error}", "error")
    finally:
        connection.close()
    return redirect(url_for("main.index"))


@bp.post("/migrate-to-mongodb")
def migrate_to_mongodb():
    connection = db.get_mysql_connection()
    try:
        counts = migrate_sql_to_mongo(connection, db.get_mongo_database())
        flash(
            f"Migrated {counts['clubs']} clubs, {counts['seasons']} seasons and "
            f"{counts['matches']} matches to MongoDB.",
            "success",
        )
    except Exception as error:  # noqa: BLE001
        flash(f"Migration failed: {error}", "error")
    finally:
        connection.close()
    return redirect(url_for("main.index"))
