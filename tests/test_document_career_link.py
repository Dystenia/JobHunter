from jobhunter.core import Base, database
from jobhunter.career import save_document, list_documents
from jobhunter.entries import save_entry, entries


def test_document_source_remains_unverified(tmp_path):
    engine = database(tmp_path / "source.db")
    Base.metadata.create_all(engine)
    save_document(engine, "certificate.pdf", "Python course", "pdf")
    doc_id = list_documents(engine)[0][0]
    save_entry(engine, "Zertifikat", "Python course", details="Python course",
               verified=False, source_document_id=doc_id)
    row = entries(engine)[0]
    assert row[6] is False
    assert row[7] == doc_id
