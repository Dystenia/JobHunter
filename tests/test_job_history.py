from jobhunter.core import Base, database, add_job, list_jobs, set_status, list_rejected, list_status_events

def test_reject_and_restore(tmp_path):
    engine = database(tmp_path / "jobs.db")
    Base.metadata.create_all(engine)
    assert add_job(engine, "Python Developer", "Example", "", "Python")
    job_id = list_jobs(engine)[0][0]
    set_status(engine, job_id, "rejected")
    assert list_rejected(engine)[0][0] == job_id
    set_status(engine, job_id, "new")
    assert list_rejected(engine) == []
    events = list_status_events(engine, job_id)
    assert [(e[0], e[1]) for e in events] == [("rejected", "new"), ("new", "rejected")]
