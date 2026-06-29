"""
Validation Script for Milestone 2 (IdentityService)
Runs isolated test cases against the IdentityService module and verifies DB writes.
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, SessionLocal
from src.services.face_service import FaceService
from src.services.identity_service import IdentityService
from src.schemas.identity import Role, AuthenticationStatus
from src.models.authentication_log import AuthenticationLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("validation")

def run_tests():
    init_db()
    db = SessionLocal()
    
    # 1. Initialize dependencies
    face_service = FaceService(known_faces_dir="known_faces", tolerance=0.50)
    identity_service = IdentityService(face_service)
    
    try:
        # Clear previous auth logs for clean testing
        logger.info("Clearing previous authentication logs for testing...")
        db.query(AuthenticationLog).delete()
        db.commit()

        # --- Test Case 1: Invalid Barcode Format ---
        logger.info("Testing invalid format: 'ABC'...")
        res = identity_service.authenticate(barcode="ABC", frame=None, db=db, skip_face_verification=True)
        assert not res.authenticated
        assert res.rejection_reason == AuthenticationStatus.INVALID_FORMAT
        assert res.identity is None
        logger.info("✓ Test Case 1 Passed.")

        # --- Test Case 2: Unknown Barcode ---
        logger.info("Testing unknown barcode: 'SET-99999'...")
        res = identity_service.authenticate(barcode="SET-99999", frame=None, db=db, skip_face_verification=True)
        assert not res.authenticated
        assert res.rejection_reason == AuthenticationStatus.UNKNOWN_BARCODE
        assert res.identity is None
        logger.info("✓ Test Case 2 Passed.")

        # --- Test Case 3: Faculty Authentication ---
        logger.info("Testing faculty scan: 'FAC-01'...")
        res = identity_service.authenticate(barcode="FAC-01", frame=None, db=db, skip_face_verification=True)
        assert res.authenticated
        assert res.rejection_reason == AuthenticationStatus.SUCCESS
        assert res.identity is not None
        assert res.identity.role == Role.FACULTY
        assert res.identity.name == "Dr. Adheem"
        logger.info("✓ Test Case 3 Passed.")

        # --- Test Case 4: Valid Student (skip face verification) ---
        logger.info("Testing student scan: 'SET-12584'...")
        res = identity_service.authenticate(barcode="SET-12584", frame=None, db=db, skip_face_verification=True)
        assert res.authenticated
        assert res.rejection_reason == AuthenticationStatus.SUCCESS
        assert res.identity is not None
        assert res.identity.role == Role.STUDENT
        assert res.identity.name == "Sanjaynath"
        logger.info("✓ Test Case 4 Passed.")


        # Commit transactions to verify database persistence
        db.commit()

        # --- Database Verification ---
        logger.info("Verifying database records in authentication_logs...")
        logs = db.query(AuthenticationLog).order_by(AuthenticationLog.id.asc()).all()
        assert len(logs) == 4
        
        # Log 1: ABC
        assert logs[0].barcode_scanned == "ABC"
        assert logs[0].actor_type == "UNKNOWN"
        assert logs[0].status == "INVALID_FORMAT"
        
        # Log 2: SET-99999
        assert logs[1].barcode_scanned == "SET-99999"
        assert logs[1].actor_type == "UNKNOWN"
        assert logs[1].status == "UNKNOWN_BARCODE"
        
        # Log 3: FAC-01
        assert logs[2].barcode_scanned == "FAC-01"
        assert logs[2].resolved_id == "FAC-01"
        assert logs[2].actor_type == "FACULTY"
        assert logs[2].status == "SUCCESS"
        
        # Log 4: SET-12584
        assert logs[3].barcode_scanned == "SET-12584"
        assert logs[3].resolved_id == "SET-12584"
        assert logs[3].actor_type == "STUDENT"
        assert logs[3].status == "SUCCESS"
        
        logger.info("✓ Database verification checks passed.")
        logger.info("--- ALL IDENTITY SERVICE VALIDATION CHECKS PASSED ---")

    except AssertionError as e:
        logger.error("Assertion failed during validation.")
        raise e
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
