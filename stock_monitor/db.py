from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args: dict[str, object] = {}
if settings.database_url.startswith('sqlite'):
    connect_args = {'check_same_thread': False, 'timeout': 30}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True,
    pool_pre_ping=True,
)

if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _ensure_sqlite_directory() -> None:
    if not settings.database_url.startswith('sqlite:///'):
        return

    sqlite_path = settings.database_url.removeprefix('sqlite:///')
    if sqlite_path == ':memory:' or sqlite_path.startswith('file:'):
        return

    Path(sqlite_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    from . import models  # noqa: F401

    _ensure_sqlite_directory()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
