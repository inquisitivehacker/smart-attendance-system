"""
Seeding Script for Faculty Records (Milestone 1)
Populates the 'faculty' table with development/demo records.
"""
import logging
from src.database import SessionLocal
from src.models.faculty import Faculty

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("seeding")

def seed_faculty():
    db = SessionLocal()
    try:
        # Check if FAC-01 already exists
        faculty_id = "FAC-01"
        existing = db.query(Faculty).filter(Faculty.id == faculty_id).first()
        
        if existing:
            logger.info(f"Faculty record '{faculty_id}' already exists: {existing.name} ({existing.department}). Skipping.")
            return
            
        logger.info(f"Seeding faculty record: '{faculty_id}'...")
        new_faculty = Faculty(
            id=faculty_id,
            name="Dr. Adheem",
            department="Computer Science"
        )
        db.add(new_faculty)
        db.commit()
        logger.info("Faculty seeded successfully.")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_faculty()
