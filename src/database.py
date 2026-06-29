"""
SQLite database engine and session factory.
WAL mode enabled for concurrent read/write support.
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


# Enable WAL mode and busy timeout on every new connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI dependency: yields a DB session, auto-closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once on startup."""
    # Import models so Base.metadata knows about them
    import src.models.student  # noqa: F401
    import src.models.session  # noqa: F401
    import src.models.attendance  # noqa: F401
    import src.models.scan_log  # noqa: F401
    import src.models.student_state  # noqa: F401
    import src.models.system_status  # noqa: F401
    import src.models.faculty  # noqa: F401
    import src.models.presence_event  # noqa: F401
    import src.models.student_presence_state  # noqa: F401
    import src.models.authentication_log  # noqa: F401

    Base.metadata.create_all(bind=engine)

