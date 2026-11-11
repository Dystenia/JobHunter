import pytest
from jobhunter.core import database, Base
from jobhunter.career import CareerDocument, save_document, list_documents, update_document, delete_document

def test_document_management(tmp_path):
    engine = database(tmp_path / "documents.db")
    Base.metadata.create_all(engine)
    save_document(engine, "cv.pdf", "Original", "pdf")
    doc_id = list_documents(engine)[0][0]
    update_document(engine, doc_id, "Korrigierter Text")
    assert list_documents(engine)[0][3] == "Korrigierter Text"
    with pytest.raises(ValueError):
        update_document(engine, doc_id, " ")
    delete_document(engine, doc_id)
    assert list_documents(engine) == []
