import os

import psycopg
from psycopg.rows import dict_row
from pymongo import MongoClient

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://skillsync:skillsync@localhost:5432/skillsync",
)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "skillsync")

mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
mongo_db = mongo[MONGO_DB]
profiles = mongo_db["user_portfolios"]
contexts = mongo_db["project_context"]


def pg_conn() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)
