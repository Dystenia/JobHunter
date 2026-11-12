import pytest
from jobhunter.mailer import build_message, log_mail, mail_history
from jobhunter.core import database, Base


def test_message_with_attachment(tmp_path):
    attachment = tmp_path / "cv.pdf"
    attachment.write_bytes(b"%PDF-test")
    message = build_message("sender@example.org", "jobs@example.org", "Application", "Hello", [attachment])
    assert message["To"] == "jobs@example.org"
    assert len(list(message.iter_attachments())) == 1
    assert list(message.iter_attachments())[0].get_filename() == "cv.pdf"


def test_reject_header_injection():
    with pytest.raises(ValueError):
        build_message("sender@example.org", "jobs@example.org", "Hi\\r\\nBcc: attacker@example.org", "Hello")


def test_mail_audit(tmp_path):
    engine = database(tmp_path / "mail.db")
    Base.metadata.create_all(engine)
    log_mail(engine, "jobs@example.org", "Application", "sent")
    assert mail_history(engine)[0][3] == "sent"
