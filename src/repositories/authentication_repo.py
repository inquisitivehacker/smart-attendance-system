from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from src.models.authentication_log import AuthenticationLog
from src.schemas.identity import Role, AuthenticationStatus


class AuthenticationRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def log_attempt(
        self,
        barcode: str,
        resolved_id: str | None,
        role: Role,
        face_verified: bool,
        face_confidence: float | None,
        status: AuthenticationStatus
    ) -> AuthenticationLog:
        log = AuthenticationLog(
            barcode_scanned=barcode,
            resolved_id=resolved_id,
            actor_type=role.value,
            face_verified=1 if face_verified else 0,
            face_confidence=face_confidence,
            status=status.value,
            scanned_at=datetime.utcnow()
        )
        self.db.add(log)
        return log
