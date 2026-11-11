from jobhunter.core import database, Base
from jobhunter.entries import CareerEntry, entries, save_entry, remove_entry
import pytest

def test_career_records(tmp_path):
    engine = database(tmp_path / "career.db")
    Base.metadata.create_all(engine)
    save_entry(engine, "Projekt", "JobHunter", details="Python", verified=False)
    item = entries(engine)[0]
    assert item[2] == "JobHunter" and item[6] is False
    save_entry(engine, "Projekt", "JobHunter", details="PySide6", verified=True, entry_id=item[0])
    assert entries(engine)[0][6] is True
    remove_entry(engine, item[0])
    assert entries(engine) == []

def test_invalid_category(tmp_path):
    engine = database(tmp_path / "career.db")
    Base.metadata.create_all(engine)
    with pytest.raises(ValueError):
        save_entry(engine, "Erfunden", "Test")
