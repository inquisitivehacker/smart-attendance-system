"""
Seed script — creates Student records from existing known_faces/ folders.
Also marks face_enrolled = 1 for students with photos.

Usage:
    python -m scripts.seed_students
"""
import os
import sys
import glob

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, SessionLocal
from src.repositories.student_repo import StudentRepository

KNOWN_FACES_DIR = "known_faces"

# Map folder names to human-readable names
# Update this dict with real student names
STUDENT_NAMES = {
    "SET-12584": "Sanjay",
    "SET-12765": "Student 2",
    "22BTTCO001": "Student 3",
}


def seed():
    init_db()
    db = SessionLocal()
    repo = StudentRepository(db)

    if not os.path.isdir(KNOWN_FACES_DIR):
        print(f"Error: {KNOWN_FACES_DIR}/ directory not found")
        return

    created = 0
    skipped = 0

    for folder in os.listdir(KNOWN_FACES_DIR):
        folder_path = os.path.join(KNOWN_FACES_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        if repo.exists(folder):
            print(f"  ⏭️  Skip (exists): {folder}")
            skipped += 1
            continue

        # Get name from mapping, or use folder name as fallback
        name = STUDENT_NAMES.get(folder, folder)

        # Create student
        repo.create(student_id=folder, name=name)

        # Check if face photos exist
        photos = (
            glob.glob(f"{folder_path}/*.jpg")
            + glob.glob(f"{folder_path}/*.png")
            + glob.glob(f"{folder_path}/*.jpeg")
        )
        if photos:
            repo.mark_face_enrolled(folder)
            print(f"  ✅ Created: {folder} ({name}) — {len(photos)} photos enrolled")
        else:
            print(f"  ⚠️  Created: {folder} ({name}) — NO photos found")

        created += 1

    db.close()
    print(f"\nDone: {created} created, {skipped} skipped")


if __name__ == "__main__":
    seed()
