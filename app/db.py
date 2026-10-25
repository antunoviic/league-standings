"""Database connections for MariaDB (relational) and MongoDB (document store)."""

import os
from functools import lru_cache

import pymysql
from pymongo import MongoClient


def get_mysql_connection():
    """Open a new MariaDB connection. Callers are responsible for closing it."""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "league"),
        password=os.getenv("MYSQL_PASSWORD", "league"),
        database=os.getenv("MYSQL_DATABASE", "league"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@lru_cache(maxsize=1)
def _mongo_client() -> MongoClient:
    # MongoClient keeps its own connection pool, so one instance per process is enough.
    return MongoClient(
        host=os.getenv("MONGO_HOST", "localhost"),
        port=int(os.getenv("MONGO_PORT", "27017")),
    )


def get_mongo_database():
    return _mongo_client()[os.getenv("MONGO_DATABASE", "league")]
