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
from src.database import engine, init_db, Base

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
        
        # Check 'attendance' table columns
        attendance_cols = []
        if "attendance" in existing_tables:
            attendance_cols = [c["name"] for c in inspector.get_columns("attendance")]
        logger.info(f"Existing columns in 'attendance': {attendance_cols}")
        
        if "attendance_percentage" not in attendance_cols:
            logger.info("Adding 'attendance_percentage' column to 'attendance' table...")
            cursor.execute("ALTER TABLE attendance ADD COLUMN attendance_percentage REAL")
            conn.commit()
            logger.info("Column 'attendance_percentage' added.")

        if "duration_seconds" not in attendance_cols:
            logger.info("Adding 'duration_seconds' column to 'attendance' table...")
            cursor.execute("ALTER TABLE attendance ADD COLUMN duration_seconds INTEGER")
            conn.commit()
            logger.info("Column 'duration_seconds' added.")

        # Check 'sessions' table columns
        sessions_cols = []
        if "sessions" in existing_tables:
            sessions_cols = [c["name"] for c in inspector.get_columns("sessions")]
        logger.info(f"Existing columns in 'sessions': {sessions_cols}")
        
        if "faculty_id" not in sessions_cols:
            logger.info("Adding 'faculty_id' column to 'sessions' table...")
            cursor.execute("ALTER TABLE sessions ADD COLUMN faculty_id TEXT REFERENCES faculty(id)")
            conn.commit()
            logger.info("Column 'faculty_id' added.")

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
    # Check attendance columns
    cursor.execute("PRAGMA table_info(attendance)")
    att_info = {r[1]: r[2] for r in cursor.fetchall()}
    logger.info(f"PRAGMA table_info(attendance): {att_info}")
    
    if "attendance_percentage" not in att_info or att_info["attendance_percentage"] != "REAL":
        raise ValueError("Validation failed: column 'attendance_percentage' (REAL) is missing or has incorrect type in 'attendance'.")
    if "duration_seconds" not in att_info or att_info["duration_seconds"] != "INTEGER":
        raise ValueError("Validation failed: column 'duration_seconds' (INTEGER) is missing or has incorrect type in 'attendance'.")
    logger.info("✓ New attendance columns verified.")

    # Check sessions columns
    cursor.execute("PRAGMA table_info(sessions)")
    sess_info = {r[1]: r[2] for r in cursor.fetchall()}
    logger.info(f"PRAGMA table_info(sessions): {sess_info}")
    
    if "faculty_id" not in sess_info or sess_info["faculty_id"] != "TEXT":
        raise ValueError("Validation failed: column 'faculty_id' (TEXT) is missing or has incorrect type in 'sessions'.")
    logger.info("✓ New sessions columns verified.")

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
