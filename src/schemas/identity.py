from enum import Enum
from pydantic import BaseModel


class Role(str, Enum):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    UNKNOWN = "UNKNOWN"


class AuthenticationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    UNKNOWN_BARCODE = "UNKNOWN_BARCODE"
    INVALID_FORMAT = "INVALID_FORMAT"
    REJECTED_FACE = "REJECTED_FACE"


class Identity(BaseModel):
    id: str
    name: str
    role: Role

    model_config = {"from_attributes": True}


class AuthenticationResult(BaseModel):
    authenticated: bool
    rejection_reason: AuthenticationStatus
    confidence: float | None = None
    identity: Identity | None = None

    model_config = {"from_attributes": True}
