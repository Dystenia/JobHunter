from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Text, Integer, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="new")
    created_at: Mapped[str] = mapped_column(String(40), default=lambda: datetime.now(timezone.utc).isoformat())

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    skills: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[str] = mapped_column(Text, default="")

def database(path: str | Path = "jobhunter.db"):
    engine = create_engine("sqlite:///" + str(Path(path).resolve()))
    Base.metadata.create_all(engine)
    return engine

def fingerprint(title: str, company: str, url: str) -> str:
    normalized = "|".join(x.strip().lower() for x in (title, company, url))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def terms(text: str) -> set[str]:
    return set(re.findall(r"[\w+#.-]{2,}", text.casefold()))

def match_score(description: str, skills: str) -> int:
    wanted = terms(skills.replace(",", " "))
    if not wanted:
        return 0
    found = terms(description)
    return round(100 * len(wanted & found) / len(wanted))

def add_job(engine, title: str, company: str, url: str, description: str) -> bool:
    title = title.strip()
    if not title:
        raise ValueError("Stellentitel fehlt")
    key = fingerprint(title, company, url)
    with Session(engine) as session:
        if session.scalar(select(Job).where(Job.fingerprint == key)):
            return False
        profile = session.get(Profile, 1)
        score = match_score(description + " " + title, profile.skills if profile else "")
        session.add(Job(fingerprint=key, title=title, company=company.strip(),
                        url=url.strip(), description=description, score=score))
        session.commit()
    return True

def save_profile(engine, skills: str, experience: str):
    with Session(engine) as session:
        profile = session.get(Profile, 1)
        if profile is None:
            profile = Profile(id=1)
            session.add(profile)
        profile.skills, profile.experience = skills, experience
        for job in session.scalars(select(Job)):
            job.score = match_score(job.description + " " + job.title, skills)
        session.commit()

def list_jobs(engine):
    with Session(engine) as session:
        return [(j.id, j.title, j.company, j.score, j.status, j.url)
                for j in session.scalars(select(Job).order_by(Job.score.desc(), Job.id.desc()))]

def set_status(engine, job_id: int, status: str):
    if status not in {"new", "queued", "applied", "rejected"}:
        raise ValueError("Ungültiger Status")
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job is None:
            raise ValueError("Stelle nicht gefunden")
        job.status = status
        session.commit()
