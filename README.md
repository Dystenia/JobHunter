# JobHunter — AI Job Hunter & Application Studio

Open-source Windows desktop application for managing job opportunities, comparing them with a verified career profile and preparing applications.

## Current MVP
- PySide6 desktop interface
- Local SQLite persistence with SQLAlchemy
- Manual job entry and duplicate detection
- Editable skills and experience profile
- Transparent keyword-based matching (not an AI assessment)
- Application queue with new / queued / applied / rejected statuses
- Unit tests for persistence, deduplication and matching

## Quick start (Windows PowerShell)
```powershell
git clone https://github.com/Dystenia/JobHunter.git
cd JobHunter
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Run tests: `python -m pytest -q`

## Planned
Job source adapters, structured requirement extraction, explainable AI matching, DOCX/PDF application documents, scheduled background jobs, safe cancellation and resume.

## Privacy
Local databases, generated documents, API keys and personal profiles must not be committed. See `.gitignore`. The repository contains no personal application data.

## Notes
The current score is a simple token overlap of skills and job descriptions; it does not infer years of experience, qualification equivalence or seniority. No automatic applications are submitted.
