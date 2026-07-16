"""
Database Migration Script (Milestone 1)
Handles backing up database, schema inspection using SQLAlchemy, executing necessary SQL ALTER commands,
and performing detailed validation checks (including foreign key checks and table column verification).
"""
import os
import shutil
import logging
import sqlite3
from sqlalchemy import inspect
from src.database import engine, init_db

SCHEMA_MIGRATIONS = {
    "attendance": {
        "attendance_percentage": {"sql_def": "REAL", "base_type": "REAL"},
        "duration_seconds": {"sql_def": "INTEGER", "base_type": "INTEGER"},
        "late_minutes": {"sql_def": "INTEGER", "base_type": "INTEGER"},
        "early_departure_minutes": {"sql_def": "INTEGER", "base_type": "INTEGER"},
        "regularization_required": {"sql_def": "INTEGER", "base_type": "INTEGER"},
        "policy_version": {"sql_def": "TEXT", "base_type": "TEXT"},
        "computed_at": {"sql_def": "TEXT", "base_type": "TEXT"},
    },
    "sessions": {
        "faculty_id": {"sql_def": "TEXT REFERENCES faculty(id)", "base_type": "TEXT"},
    }
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("migration")

DB_PATH = "data/attendance.db"
BACKUP_PATH = "data/attendance.backup.db"

def backup_database():
    """Copy the database to a backup file."""
    if not os.path.exists(DB_PATH):
        logger.info(f"Database file '{DB_PATH}' not found. No backup needed.")
        return False
        
    logger.info(f"Backing up database: '{DB_PATH}' -> '{BACKUP_PATH}'...")
    shutil.copy(DB_PATH, BACKUP_PATH)
    logger.info("Backup created successfully.")
    return True

def run_migration():
    # 1. Back up database
    backup_created = backup_database()

    try:
        # 2. Inspect database tables and columns
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables discovered: {existing_tables}")

        # 3. Create missing tables using SQLAlchemy
        logger.info("Creating new tables via SQLAlchemy metadata...")
        init_db()
        logger.info("Table creation step completed.")

        # 4. Check and add new columns to existing tables using raw SQLite queries
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Re-fetch existing tables/columns to handle fresh db creation
        existing_tables = inspect(engine).get_table_names()
        
        for table_name, columns in SCHEMA_MIGRATIONS.items():
            if table_name in existing_tables:
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_cols = [r[1] for r in cursor.fetchall()]
                logger.info(f"Existing columns in '{table_name}': {existing_cols}")
                
                for col_name, col_attrs in columns.items():
                    if col_name not in existing_cols:
                        sql_def = col_attrs["sql_def"]
                        logger.info(f"Adding '{col_name}' column to '{table_name}' table...")
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sql_def}")
                        logger.info(f"Column '{col_name}' added.")
        
        # Commit all schema changes at once
        conn.commit()

        cursor.close()
        conn.close()

        # 5. Run Validation
        validate_migration()
        logger.info("--- MIGRATION COMPLETED SUCCESSFULLY ---")

    except Exception as e:
        logger.error(f"--- MIGRATION FAILED: {e} ---")
        if backup_created:
            logger.error("ROLLBACK REQUIRED. Execute the following commands to restore your database:")
            logger.error(f"  mv {BACKUP_PATH} {DB_PATH}")
        raise e

def validate_migration():
    logger.info("--- STARTING SCHEMA VALIDATION ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # A. Verify tables exist
    expected_tables = ["faculty", "presence_events", "student_presence_states", "authentication_logs", "attendance", "sessions"]
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    actual_tables = [r[0] for r in cursor.fetchall()]
    
    for table in expected_tables:
        if table not in actual_tables:
            raise ValueError(f"Validation failed: expected table '{table}' is missing from the database.")
        logger.info(f"✓ Table '{table}' verified.")

    # B. Verify columns exist via PRAGMA table_info
    for table_name, columns in SCHEMA_MIGRATIONS.items():
        cursor.execute(f"PRAGMA table_info({table_name})")
        table_info = {r[1]: r[2] for r in cursor.fetchall()}
        logger.info(f"PRAGMA table_info({table_name}): {table_info}")
        
        for col_name, col_attrs in columns.items():
            expected_type = col_attrs["base_type"]
            
            # Special case for FLOAT/REAL and BOOLEAN/INTEGER due to SQLAlchemy mappings in SQLite
            allowed_types = [expected_type]
            if expected_type == "REAL":
                allowed_types.append("FLOAT")
            elif expected_type == "INTEGER":
                allowed_types.append("BOOLEAN")
                
            if col_name not in table_info:
                raise ValueError(f"Validation failed: column '{col_name}' is missing in '{table_name}'.")
            if table_info[col_name] not in allowed_types:
                raise ValueError(f"Validation failed: column '{col_name}' ({'/'.join(allowed_types)}) has incorrect type in '{table_name}' (found {table_info.get(col_name)}).")
        logger.info(f"✓ New {table_name} columns verified.")

    # C. Run Foreign Key Check
    logger.info("Running PRAGMA foreign_key_check...")
    cursor.execute("PRAGMA foreign_key_check")
    violations = cursor.fetchall()
    if violations:
        raise ValueError(f"Validation failed: Foreign Key violations discovered: {violations}")
    logger.info("✓ Foreign Key check passed with 0 violations.")

    cursor.close()
    conn.close()
    logger.info("--- SCHEMA VALIDATION PASSED ---")

if __name__ == "__main__":
    run_migration()
