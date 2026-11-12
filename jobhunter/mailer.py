from __future__ import annotations
import json
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
import keyring
from sqlalchemy import Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from .core import Base

SERVICE = "JobHunter.SMTP"
SETTINGS_PATH = Path(__file__).resolve().parent.parent / "smtp_settings.json"

class MailLog(Base):
    __tablename__ = "mail_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))
    details: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[str] = mapped_column(String(40), default=lambda: datetime.now(timezone.utc).isoformat())

def load_settings():
    if not SETTINGS_PATH.is_file():
        return {"host": "", "port": 587, "security": "STARTTLS", "username": "", "sender": "", "signature": ""}
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))

def save_settings(settings, password=None):
    allowed = ("host", "port", "security", "username", "sender", "signature")
    data = {k: settings.get(k, "") for k in allowed}
    if data["security"] not in ("STARTTLS", "SSL/TLS"):
        raise ValueError("Ungültige TLS-Einstellung")
    data["port"] = int(data["port"])
    if not 1 <= data["port"] <= 65535:
        raise ValueError("Ungültiger SMTP-Port")
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if password is not None and password:
        keyring.set_password(SERVICE, data["username"], password)

def validate_address(address):
    name, email = parseaddr(address.strip())
    if not email or "@" not in email or "\r" in address or "\n" in address or email != address.strip():
        raise ValueError("Bitte eine einzelne gültige E-Mail-Adresse eingeben.")
    return email

def build_message(sender, recipient, subject, body, attachments=()):
    sender, recipient = validate_address(sender), validate_address(recipient)
    if not subject.strip() or "\r" in subject or "\n" in subject:
        raise ValueError("Betreff fehlt oder ist ungültig.")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject.strip()
    message.set_content(body)
    for attachment in attachments:
        path = Path(attachment)
        if not path.is_file():
            raise FileNotFoundError(f"Anhang fehlt: {path.name}")
        # Attach binary; do not interpret or execute attachments.
        message.add_attachment(path.read_bytes(), maintype="application",
                               subtype="octet-stream", filename=path.name)
    return message

def test_connection(settings, password=None):
    host = str(settings.get("host", "")).strip()
    username = str(settings.get("username", "")).strip()
    sender = validate_address(str(settings.get("sender", "")))
    security = settings.get("security", "STARTTLS")
    port = int(settings.get("port", 587))
    if not host or not username or not 1 <= port <= 65535 or security not in ("STARTTLS", "SSL/TLS"):
        raise ValueError("SMTP-Host, Port, Benutzername und TLS-Modus prüfen.")
    secret = password or keyring.get_password(SERVICE, username)
    if not secret:
        raise ValueError("SMTP-Passwort fehlt.")
    context = ssl.create_default_context()
    if security == "SSL/TLS":
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as smtp:
            smtp.login(username, secret)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            if not smtp.has_extn("starttls"):
                raise RuntimeError("STARTTLS wird vom Server nicht angeboten.")
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(username, secret)
    return True


def send_mail(settings, recipient, subject, body, attachments=()):
    host = str(settings.get("host", "")).strip()
    username = str(settings.get("username", "")).strip()
    sender = settings.get("sender", "")
    security = settings.get("security", "STARTTLS")
    port = int(settings.get("port", 587))
    if not host or not username or security not in ("STARTTLS", "SSL/TLS"):
        raise ValueError("SMTP-Server, Benutzername und TLS-Modus konfigurieren.")
    password = keyring.get_password(SERVICE, username)
    if not password:
        raise ValueError("Kein SMTP-Passwort im Windows-Anmeldedatenspeicher gefunden.")
    message = build_message(sender, recipient, subject, body, attachments)
    context = ssl.create_default_context()
    if security == "SSL/TLS":
        with smtplib.SMTP_SSL(host, port, timeout=25, context=context) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=25) as smtp:
            smtp.ehlo()
            if not smtp.has_extn("starttls"):
                raise RuntimeError("SMTP-Server bietet kein STARTTLS an. Versand abgebrochen.")
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)

def log_mail(engine, recipient, subject, status, details=""):
    with Session(engine) as session:
        session.add(MailLog(recipient=recipient, subject=subject, status=status, details=details[:500]))
        session.commit()

def mail_history(engine):
    with Session(engine) as session:
        return [(r.sent_at, r.recipient, r.subject, r.status)
                for r in session.scalars(select(MailLog).order_by(MailLog.id.desc()).limit(100))]
