import sqlite3
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# SQLite database path
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "bi_agent.db"


def get_connection():
    """
    Create and return a SQLite database connection.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """
    Initialize the database and create the required tables.
    """
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ========================================================
        # DATASETS
        # ========================================================

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

        # ========================================================
        # ANALYSIS HISTORY
        # ========================================================

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

        # ========================================================
        # SQL QUERIES
        # ========================================================

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

        # ========================================================
        # BUSINESS INSIGHTS
        # ========================================================

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

        # ========================================================
        # DATASET HEALTH HISTORY
        #
        # Stores historical health snapshots used by:
        # - Health Trend & Comparison
        # - Dataset Health Timeline
        # - Timeline statistics
        # - Trend intelligence
        # ========================================================

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


        # --------------------------------------------------------
        # SAFE MIGRATION: health_history.flagged_columns
        #
        # Existing snapshots remain intact. Historical values
        # stay NULL because their original counts are unknown.
        # --------------------------------------------------------

        cursor.execute("PRAGMA table_info(health_history)")
        health_history_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        if "flagged_columns" not in health_history_columns:
            cursor.execute("""
                ALTER TABLE health_history
                ADD COLUMN flagged_columns INTEGER DEFAULT NULL
            """)


        connection.commit()

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print(
        f"Database initialized successfully: {DATABASE_PATH}"
    )
