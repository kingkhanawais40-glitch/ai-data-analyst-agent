import os
import re
import sqlite3
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "bi_agent.db"

# SQLite remains the default for local development and tests.
# Set DATABASE_BACKEND=postgres in the production environment.
DATABASE_BACKEND = os.getenv(
    "DATABASE_BACKEND", "sqlite"
).strip().lower()

DATABASE_URL = os.getenv("DATABASE_URL")


# ============================================================
# POSTGRESQL COMPATIBILITY LAYER
# ============================================================

class PostgresCursor:
    """Adapt existing SQLite-style queries for PostgreSQL."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, sql, parameters=None):
        self.lastrowid = None

        statement = sql
        normalized = statement.lstrip().upper()

        # Preserve cursor.lastrowid for the two existing
        # insert operations that depend on it.
        needs_inserted_id = (
            normalized.startswith("INSERT INTO DATASETS")
            or normalized.startswith(
                "INSERT INTO ANALYSIS_HISTORY"
            )
        ) and "RETURNING" not in normalized

        if needs_inserted_id:
            statement = statement.rstrip().rstrip(";")
            statement += " RETURNING id"

        # Convert existing parameter placeholders.
        statement = re.sub(r"\?", "%s", statement)

        if parameters is None:
            self._cursor.execute(statement)
        else:
            self._cursor.execute(statement, parameters)

        if needs_inserted_id:
            row = self._cursor.fetchone()
            self.lastrowid = row["id"] if row else None

        return self

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnection:
    """Keep the existing connection interface compatible."""

    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return PostgresCursor(self._connection.cursor())

    def __getattr__(self, name):
        return getattr(self._connection, name)


# ============================================================
# CONNECTION FACTORY
# ============================================================

def get_connection():
    """Return a SQLite or PostgreSQL-compatible connection."""

    if DATABASE_BACKEND == "sqlite":
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        return connection

    if DATABASE_BACKEND == "postgres":
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is required when "
                "DATABASE_BACKEND=postgres."
            )

        connection = psycopg.connect(
            DATABASE_URL,
            connect_timeout=10,
            row_factory=dict_row,
        )

        return PostgresConnection(connection)

    raise RuntimeError(
        "Unsupported DATABASE_BACKEND. "
        "Use 'sqlite' or 'postgres'."
    )


# ============================================================
# SQLITE SCHEMA
# ============================================================

def _initialize_sqlite(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            column_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(datasets)")

    dataset_columns = {
        row["name"] for row in cursor.fetchall()
    }

    if "blob_pathname" not in dataset_columns:
        cursor.execute("""
            ALTER TABLE datasets
            ADD COLUMN blob_pathname TEXT
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sql_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            insight TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            quality_score REAL DEFAULT 0,
            anomaly_percentage REAL DEFAULT 0,
            anomalous_records INTEGER DEFAULT 0,
            anomaly_columns INTEGER DEFAULT 0,
            total_outlier_occurrences INTEGER DEFAULT 0,
            total_missing_values INTEGER DEFAULT 0,
            duplicate_rows INTEGER DEFAULT 0,
            flagged_columns INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )
    """)

    cursor.execute("PRAGMA table_info(health_history)")

    columns = {
        row["name"] for row in cursor.fetchall()
    }

    if "flagged_columns" not in columns:
        cursor.execute("""
            ALTER TABLE health_history
            ADD COLUMN flagged_columns INTEGER DEFAULT NULL
        """)


# ============================================================
# POSTGRESQL SCHEMA
# ============================================================

def _initialize_postgres(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            column_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
    """, ("datasets",))

    dataset_columns = {
        row["column_name"] for row in cursor.fetchall()
    }

    if "blob_pathname" not in dataset_columns:
        cursor.execute("""
            ALTER TABLE datasets
            ADD COLUMN blob_pathname TEXT
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES datasets(id),
            question TEXT NOT NULL,
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sql_queries (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES datasets(id),
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES datasets(id),
            insight TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_history (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES datasets(id),
            quality_score DOUBLE PRECISION DEFAULT 0,
            anomaly_percentage DOUBLE PRECISION DEFAULT 0,
            anomalous_records INTEGER DEFAULT 0,
            anomaly_columns INTEGER DEFAULT 0,
            total_outlier_occurrences INTEGER DEFAULT 0,
            total_missing_values INTEGER DEFAULT 0,
            duplicate_rows INTEGER DEFAULT 0,
            flagged_columns INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
    """, ("health_history",))

    columns = {
        row["column_name"] for row in cursor.fetchall()
    }

    if "flagged_columns" not in columns:
        cursor.execute("""
            ALTER TABLE health_history
            ADD COLUMN flagged_columns INTEGER DEFAULT NULL
        """)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():
    """Create required tables and safely migrate the schema."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        if DATABASE_BACKEND == "sqlite":
            _initialize_sqlite(cursor)
        else:
            _initialize_postgres(cursor)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print(
        f"Database initialized successfully "
        f"(backend: {DATABASE_BACKEND})."
    )