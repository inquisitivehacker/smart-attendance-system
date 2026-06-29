import logging
from sqlalchemy.orm import Session as DBSession

from src.services.face_service import FaceService
from src.repositories.student_repo import StudentRepository
from src.repositories.faculty_repo import FacultyRepository
from src.repositories.authentication_repo import AuthenticationRepository
from src.schemas.identity import (
    Identity,
    AuthenticationResult,
    Role,
    AuthenticationStatus
)

logger = logging.getLogger(__name__)


class IdentityService:
    def __init__(self, face_service: FaceService):
        self.face_service = face_service

    def authenticate(
        self,
        barcode: str,
        frame,
        db: DBSession,
        skip_face_verification: bool = False
    ) -> AuthenticationResult:
        student_repo = StudentRepository(db)
        faculty_repo = FacultyRepository(db)
        auth_repo = AuthenticationRepository(db)

        # 1. Barcode format validation
        if not self._validate_barcode(barcode):
            auth_repo.log_attempt(
                barcode=barcode,
                resolved_id=None,
                role=Role.UNKNOWN,
                face_verified=False,
                face_confidence=None,
                status=AuthenticationStatus.INVALID_FORMAT
            )
            return AuthenticationResult(
                authenticated=False,
                rejection_reason=AuthenticationStatus.INVALID_FORMAT,
                confidence=None,
                identity=None
            )

        # 2. Check Faculty registry
        faculty = faculty_repo.get_by_id(barcode)
        if faculty:
            identity = Identity(
                id=faculty.id,
                name=faculty.name,
                role=Role.FACULTY
            )
            auth_repo.log_attempt(
                barcode=barcode,
                resolved_id=faculty.id,
                role=Role.FACULTY,
                face_verified=True,
                face_confidence=1.0,
                status=AuthenticationStatus.SUCCESS
            )
            return AuthenticationResult(
                authenticated=True,
                rejection_reason=AuthenticationStatus.SUCCESS,
                confidence=1.0,
                identity=identity
            )

        # 3. Check Student registry
        student = student_repo.get_by_id(barcode)
        if not student:
            auth_repo.log_attempt(
                barcode=barcode,
                resolved_id=None,
                role=Role.UNKNOWN,
                face_verified=False,
                face_confidence=None,
                status=AuthenticationStatus.UNKNOWN_BARCODE
            )
            return AuthenticationResult(
                authenticated=False,
                rejection_reason=AuthenticationStatus.UNKNOWN_BARCODE,
                confidence=None,
                identity=None
            )

        # 4. Face Verification (only for students)
        verified = False
        confidence = 0.0
        if skip_face_verification:
            verified, confidence = True, 1.0
        else:
            if frame is not None:
                verified, confidence = self.face_service.verify(frame, student.id)

        identity = Identity(
            id=student.id,
            name=student.name,
            role=Role.STUDENT
        )

        if verified:
            status = AuthenticationStatus.SUCCESS
            auth_repo.log_attempt(
                barcode=barcode,
                resolved_id=student.id,
                role=Role.STUDENT,
                face_verified=True,
                face_confidence=confidence,
                status=status
            )
            return AuthenticationResult(
                authenticated=True,
                rejection_reason=status,
                confidence=confidence,
                identity=identity
            )
        else:
            status = AuthenticationStatus.REJECTED_FACE
            auth_repo.log_attempt(
                barcode=barcode,
                resolved_id=student.id,
                role=Role.STUDENT,
                face_verified=False,
                face_confidence=confidence,
                status=status
            )
            return AuthenticationResult(
                authenticated=False,
                rejection_reason=status,
                confidence=confidence,
                identity=identity
            )

    def _validate_barcode(self, barcode: str) -> bool:
        if len(barcode) > 12 or len(barcode) < 5:
            return False
        if not barcode.startswith(("21", "22", "23", "SET", "FAC")):
            return False
        return True

