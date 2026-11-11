from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from .core import Base

class CareerDocument(Base):
    __tablename__ = "career_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    extracted_text: Mapped[str] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(String(40), default=lambda: datetime.now(timezone.utc).isoformat())

class TextSnippet(Base):
    __tablename__ = "text_snippets"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100), default="Allgemein")
    content: Mapped[str] = mapped_column(Text)

def extract_document(path: str | Path) -> tuple[str, str]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8-sig"), "text"
    if suffix == ".docx":
        from docx import Document
        doc = Document(path)
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts), "docx"
    if suffix == ".pdf":
        import fitz
        with fitz.open(path) as doc:
            text = "\n".join(page.get_text() for page in doc)
            if text.strip():
                return text, "pdf"
            pages = [page.get_pixmap(matrix=fitz.Matrix(2, 2)).pil_image() for page in doc]
        return "\n".join(_ocr(page) for page in pages), "ocr"
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        from PIL import Image
        with Image.open(path) as image:
            return _ocr(image), "ocr"
    raise ValueError("Dateityp nicht unterstützt")

def _ocr(image):
    import pytesseract
    try:
        return pytesseract.image_to_string(image, lang="deu+eng")
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR ist nicht installiert oder nicht im PATH.") from exc
    except pytesseract.TesseractError as exc:
        raise RuntimeError("OCR fehlgeschlagen. Bitte deutsche und englische Sprachdaten installieren.") from exc

def save_document(engine, filename: str, text: str, method: str):
    with Session(engine) as session:
        session.add(CareerDocument(filename=Path(filename).name, extracted_text=text, extraction_method=method))
        session.commit()

def list_documents(engine):
    with Session(engine) as session:
        return [(d.id, d.filename, d.extraction_method, d.extracted_text)
                for d in session.scalars(select(CareerDocument).order_by(CareerDocument.id.desc()))]

def save_snippet(engine, title: str, category: str, content: str):
    if not title.strip() or not content.strip():
        raise ValueError("Titel und Text dürfen nicht leer sein")
    with Session(engine) as session:
        session.add(TextSnippet(title=title.strip(), category=category.strip() or "Allgemein", content=content))
        session.commit()

def list_snippets(engine):
    with Session(engine) as session:
        return [(s.id, s.title, s.category, s.content)
                for s in session.scalars(select(TextSnippet).order_by(TextSnippet.id.desc()))]

def update_snippet(engine, snippet_id: int, title: str, category: str, content: str):
    if not title.strip() or not content.strip():
        raise ValueError("Titel und Text dürfen nicht leer sein")
    with Session(engine) as session:
        snippet = session.get(TextSnippet, snippet_id)
        if snippet is None:
            raise ValueError("Textbaustein nicht gefunden")
        snippet.title = title.strip()
        snippet.category = category.strip() or "Allgemein"
        snippet.content = content
        session.commit()

def delete_snippet(engine, snippet_id: int):
    with Session(engine) as session:
        snippet = session.get(TextSnippet, snippet_id)
        if snippet is None:
            raise ValueError("Textbaustein nicht gefunden")
        session.delete(snippet)
        session.commit()
