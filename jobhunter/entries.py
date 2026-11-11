from __future__ import annotations
from sqlalchemy import String, Text, Integer, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from .core import Base

KINDS = ("Berufserfahrung", "Ausbildung", "Zertifikat", "Projekt", "Sprache", "Qualifikation")

class CareerEntry(Base):
    __tablename__ = "career_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(250))
    organization: Mapped[str] = mapped_column(String(250), default="")
    period: Mapped[str] = mapped_column(String(100), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[int] = mapped_column(Integer, default=0)
    source_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

def entries(engine):
    with Session(engine) as session:
        return [(e.id, e.kind, e.title, e.organization, e.period, e.details, bool(e.verified), e.source_document_id)
                for e in session.scalars(select(CareerEntry).order_by(CareerEntry.id.desc()))]

def save_entry(engine, kind, title, organization="", period="", details="", verified=False, entry_id=None, source_document_id=None):
    if kind not in KINDS:
        raise ValueError("Unbekannte Kategorie")
    if not title.strip():
        raise ValueError("Bezeichnung fehlt")
    with Session(engine) as session:
        item = session.get(CareerEntry, entry_id) if entry_id is not None else CareerEntry()
        if item is None:
            raise ValueError("Eintrag existiert nicht")
        item.kind, item.title = kind, title.strip()
        item.organization, item.period, item.details = organization.strip(), period.strip(), details.strip()
        item.verified = int(bool(verified))
        if entry_id is None:
            item.source_document_id = source_document_id
            session.add(item)
        session.commit()

def remove_entry(engine, entry_id):
    with Session(engine) as session:
        item = session.get(CareerEntry, entry_id)
        if item is None:
            raise ValueError("Eintrag existiert nicht")
        session.delete(item)
        session.commit()
