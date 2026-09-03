from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional, List
from datetime import datetime
import os

DB_PATH = os.environ.get("LOCALDECK_DB", "localdeck.sqlite")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host: str
    port: int
    scheme: Optional[str]
    status_code: Optional[int]
    title: Optional[str]
    icon: Optional[str]
    name: Optional[str]
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]


def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

def upsert_service(meta: dict):
    sess = get_session()
    stmt = select(Service).where(Service.host == meta.get("host"), Service.port == meta.get("port"))
    existing = sess.exec(stmt).first()
    now = datetime.utcnow()
    if existing:
        existing.scheme = meta.get("scheme")
        existing.status_code = meta.get("status_code")
        existing.title = meta.get("title")
        existing.icon = meta.get("icon")
        existing.last_seen = now
        sess.add(existing)
        sess.commit()
        return existing
    else:
        s = Service(
            host=meta.get("host"),
            port=meta.get("port"),
            scheme=meta.get("scheme"),
            status_code=meta.get("status_code"),
            title=meta.get("title"),
            icon=meta.get("icon"),
            name=None,
            first_seen=now,
            last_seen=now,
        )
        sess.add(s)
        sess.commit()
        return s

def list_services() -> List[Service]:
    sess = get_session()
    return sess.exec(select(Service)).all()

def get_known_ports():
    sess = get_session()
    rows = sess.exec(select(Service.port)).all()
    return [r for r in {row for row in rows}]
