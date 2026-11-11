from jobhunter.core import database, add_job, list_jobs, save_profile, match_score, set_status

def test_matching():
    assert match_score("Python SQLAlchemy Docker", "Python, Docker") == 100
    assert match_score("Python", "") == 0

def test_database_and_deduplication(tmp_path):
    engine = database(tmp_path / "test.db")
    save_profile(engine, "Python, Docker", "Backend development")
    assert add_job(engine, "Developer", "Acme", "https://example.com/1", "Python Docker")
    assert not add_job(engine, "Developer", "Acme", "https://example.com/1", "Python Docker")
    rows = list_jobs(engine)
    assert len(rows) == 1
    assert rows[0][3] == 100
    set_status(engine, rows[0][0], "queued")
    assert list_jobs(engine)[0][4] == "queued"
