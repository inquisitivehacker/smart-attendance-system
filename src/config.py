"""
Application configuration via environment variables.
All hardcoded constants from the prototype are now configurable.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///data/attendance.db"

    # Hardware
    hardware_mode: bool = True
    scanner_mode: str = "evdev"  # evdev | mock
    camera_index: int = 0

    # Face Recognition
    known_faces_dir: str = "known_faces"
    face_tolerance: float = 0.50

    # Attendance
    cooldown_seconds: int = 600  # 10 minutes (preserved from prototype)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton
settings = Settings()
