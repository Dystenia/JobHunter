from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QDialog,
    QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QMessageBox, QLabel, QFileDialog, QListWidget, QComboBox, QCheckBox, QScrollArea)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from .core import database, add_job, list_jobs, set_status, list_rejected, list_status_events, save_profile, Profile
from .theme import DARK_STYLESHEET
from .career import CareerDocument, TextSnippet, extract_document, save_document, list_documents, save_snippet, list_snippets, update_snippet, delete_snippet, update_document, delete_document
from .core import Base
from .entries import CareerEntry, KINDS, entries, save_entry, remove_entry
from .mailer import MailLog, load_settings, save_settings, test_connection, send_mail, log_mail, mail_history

class JobDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stelle erfassen")
        form = QFormLayout(self)
        self.title_input = QLineEdit()
        self.company = QLineEdit()
        self.url = QLineEdit()
        self.description = QTextEdit()
        for name, widget in [("Titel", self.title_input), ("Unternehmen", self.company),
                             ("URL", self.url), ("Beschreibung", self.description)]:
            form.addRow(name, widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

class ProfileDialog(QDialog):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Karriereprofil")
        form = QFormLayout(self)
        self.skills = QTextEdit()
        self.experience = QTextEdit()
        with Session(engine) as session:
            profile = session.get(Profile, 1)
            if profile:
                self.skills.setPlainText(profile.skills)
                self.experience.setPlainText(profile.experience)
        form.addRow("Skills (kommagetrennt)", self.skills)
        form.addRow("Berufserfahrung", self.experience)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = database(Path(__file__).resolve().parent.parent / 'jobhunter.db')
        Base.metadata.create_all(self.engine)
        self.setWindowTitle("JobHunter — Application Studio")
        self.setWindowIcon(QApplication.instance().windowIcon())
        self.resize(1180, 720)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)
        hero = QLabel("⚡ JOBHUNTER  /  APPLICATION STUDIO")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        subtitle = QLabel("DEIN KARRIERE-RADAR  •  Lokale Stellenverwaltung & Matching")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        stats = QHBoxLayout()
        self.stats = []
        for _ in range(3):
            label = QLabel()
            label.setObjectName("stat")
            stats.addWidget(label)
            self.stats.append(label)
        layout.addLayout(stats)
        bar = QHBoxLayout()
        for label, callback in [("Profil", self.edit_profile), ("Karriere-Daten", self.career_entries), ("CV importieren", self.import_cv), ("Dokumentenarchiv", self.documents), ("Textbausteine", self.snippets), ("E-Mail", self.mail_studio), ("Stelle hinzufügen", self.new_job),
                                ("In Warteschlange", lambda: self.change_status("queued")),
                                ("Beworben", lambda: self.change_status("applied")),
                                ("Verwerfen", lambda: self.change_status("rejected")), ("Papierkorb", self.rejected_jobs),
                                ("Aktualisieren", self.refresh)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            if label == 'Stelle hinzufügen':
                button.setObjectName('primary')
            elif label == 'Profil':
                button.setObjectName('purple')
            elif label == 'Verwerfen':
                button.setObjectName('pink')
            bar.addWidget(button)
        layout.addLayout(bar)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Stelle", "Unternehmen", "Match %", "Status", "URL"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        rows = list_jobs(self.engine)
        self.table.setRowCount(len(rows))
        self.table.setAlternatingRowColors(True)
        self.stats[0].setText(f"◈  {len(rows)}  GEFUNDENE JOBS")
        self.stats[1].setText(f"✦  {sum(1 for r in rows if r[3] >= 70)}  MATCHES ≥ 70%")
        self.stats[2].setText(f"➤  {sum(1 for r in rows if r[4] == 'queued')}  IN WARTESCHLANGE")
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def career_entries(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Career Profile Studio — bestätigte Karriere-Daten")
        dialog.resize(860, 680)
        layout = QVBoxLayout(dialog)
        items = QListWidget()
        records = entries(self.engine)
        layout.addWidget(QLabel("Nur bestätigte Einträge dürfen später für Bewerbungen verwendet werden."))
        layout.addWidget(items)
        form = QFormLayout()
        kind = QComboBox()
        kind.addItems(KINDS)
        title = QLineEdit()
        org = QLineEdit()
        period = QLineEdit()
        period.setPlaceholderText("z.B. 2020–2024")
        details = QTextEdit()
        verified = QCheckBox("Von mir geprüft und bestätigt")
        for label, widget in [("Kategorie", kind), ("Bezeichnung", title),
                              ("Arbeitgeber / Institution", org), ("Zeitraum", period),
                              ("Beschreibung", details), ("Freigabe", verified)]:
            form.addRow(label, widget)
        layout.addLayout(form)
        def reload():
            records[:] = entries(self.engine)
            items.clear()
            for row in records:
                items.addItem(f"{'✓' if row[6] else '○'}  {row[1]} | {row[2]} | {row[3]}")
        def select(index):
            if index < 0 or index >= len(records):
                return
            record = records[index]
            kind.setCurrentText(record[1])
            title.setText(record[2])
            org.setText(record[3])
            period.setText(record[4])
            details.setPlainText(record[5])
            verified.setChecked(record[6])
        items.currentRowChanged.connect(select)
        def clear():
            items.clearSelection()
            items.setCurrentRow(-1)
            kind.setCurrentIndex(0)
            title.clear()
            org.clear()
            period.clear()
            details.clear()
            verified.setChecked(False)
        def persist():
            index = items.currentRow()
            entry_id = records[index][0] if 0 <= index < len(records) else None
            try:
                save_entry(self.engine, kind.currentText(), title.text(), org.text(),
                           period.text(), details.toPlainText(), verified.isChecked(), entry_id)
                reload()
                clear()
            except ValueError as exc:
                QMessageBox.warning(dialog, "Eingabe", str(exc))
        def delete():
            index = items.currentRow()
            if index < 0 or index >= len(records):
                return
            if QMessageBox.question(dialog, "Löschen", "Karriereeintrag löschen?") != QMessageBox.StandardButton.Yes:
                return
            remove_entry(self.engine, records[index][0])
            reload()
            clear()
        buttons = QHBoxLayout()
        for label, callback in [("Neu", clear), ("Speichern", persist), ("Löschen", delete)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        reload()
        dialog.exec()

    def import_cv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Lebenslauf oder Nachweis auswählen", "",
            "Dokumente (*.pdf *.docx *.txt *.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if not path:
            return
        try:
            text, method = extract_document(path)
            if not text.strip():
                QMessageBox.warning(self, "Import", "Kein Text erkannt. Original bleibt unverändert.")
                return
            preview = QDialog(self)
            preview.setWindowTitle("Import prüfen — noch nicht als Qualifikation bestätigt")
            preview.resize(760, 540)
            layout = QVBoxLayout(preview)
            layout.addWidget(QLabel("Erkannter Text — bitte prüfen und ggf. korrigieren:"))
            editor = QTextEdit()
            editor.setPlainText(text)
            layout.addWidget(editor)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                       QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(preview.accept)
            buttons.rejected.connect(preview.reject)
            layout.addWidget(buttons)
            if preview.exec() == QDialog.DialogCode.Accepted:
                save_document(self.engine, path, editor.toPlainText(), method)
                QMessageBox.information(self, "Importiert", "Text lokal gespeichert. Profil wurde nicht automatisch verändert.")
        except Exception as exc:
            QMessageBox.warning(self, "Importfehler", str(exc))

    def documents(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("JobHunter | Dokumentenarchiv")
        dialog.resize(1050, 670)
        layout = QVBoxLayout(dialog)
        heading = QLabel("◈  DOKUMENTENARCHIV")
        heading.setObjectName("hero")
        layout.addWidget(heading)
        hint = QLabel("Lebensläufe, Zeugnisse und Nachweise · lokal gespeichert · keine automatische Profilfreigabe")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)
        actions = QHBoxLayout()
        upload = QPushButton("＋ Dokument importieren")
        upload.setObjectName("primary")
        edit = QPushButton("Text speichern")
        transfer = QPushButton("→ Karriereeintrag erstellen")
        transfer.setObjectName("purple")
        remove = QPushButton("Dokument löschen")
        remove.setObjectName("pink")
        actions.addWidget(upload)
        actions.addWidget(edit)
        actions.addWidget(transfer)
        actions.addWidget(remove)
        layout.addLayout(actions)
        body = QHBoxLayout()
        items = QListWidget()
        items.setMinimumWidth(310)
        body.addWidget(items, 1)
        preview = QTextEdit()
        preview.setPlaceholderText("Wähle links ein Dokument aus. Hier erscheint der erkannte Text zur Korrektur.")
        body.addWidget(preview, 2)
        layout.addLayout(body)
        status = QLabel()
        status.setObjectName("subtitle")
        layout.addWidget(status)
        records = []
        def refresh_docs(select_id=None):
            records[:] = list_documents(self.engine)
            items.clear()
            for doc_id, filename, method, _ in records:
                items.addItem(f"▣  {filename}   ·   {method.upper()}   #{doc_id}")
            if not records:
                status.setText("Noch keine Dokumente vorhanden. Starte mit ＋ Dokument importieren.")
                preview.clear()
                preview.setReadOnly(True)
            else:
                status.setText(f"{len(records)} Dokument(e) gespeichert · Texte sind bearbeitbar, aber nicht als Qualifikationen bestätigt.")
                preview.setReadOnly(False)
                if select_id is not None:
                    for i, record in enumerate(records):
                        if record[0] == select_id:
                            items.setCurrentRow(i)
                            break
        def show_doc(index):
            preview.setPlainText(records[index][3] if 0 <= index < len(records) else "")
        items.currentRowChanged.connect(show_doc)
        def upload_doc():
            paths, _ = QFileDialog.getOpenFileNames(
                dialog, "Dokumente importieren", "",
                "Dokumente (*.pdf *.docx *.txt *.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
            if not paths:
                return
            imported = 0
            errors = []
            for path in paths:
                try:
                    text, method = extract_document(path)
                    if not text.strip():
                        raise ValueError("Kein Text erkannt")
                    save_document(self.engine, path, text, method)
                    imported += 1
                except Exception as exc:
                    errors.append(f"{Path(path).name}: {exc}")
            refresh_docs()
            if errors:
                QMessageBox.warning(dialog, "Import", "\\n".join(errors))
            if imported:
                status.setText(f"{imported} Dokument(e) importiert. Bitte Text kontrollieren.")
        def save_text():
            index = items.currentRow()
            if index < 0 or index >= len(records):
                QMessageBox.information(dialog, "Auswahl", "Bitte zuerst ein Dokument auswählen.")
                return
            try:
                doc_id = records[index][0]
                update_document(self.engine, doc_id, preview.toPlainText())
                refresh_docs(doc_id)
                status.setText("Änderungen gespeichert. Qualifikationen bleiben unbestätigt.")
            except ValueError as exc:
                QMessageBox.warning(dialog, "Speichern", str(exc))
        def remove_doc():
            index = items.currentRow()
            if index < 0 or index >= len(records):
                return
            if QMessageBox.question(dialog, "Löschen", "Dieses importierte Dokument wirklich aus dem Archiv löschen?") != QMessageBox.StandardButton.Yes:
                return
            delete_document(self.engine, records[index][0])
            refresh_docs()
        def transfer_to_career():
            index = items.currentRow()
            if index < 0 or index >= len(records):
                QMessageBox.information(dialog, "Auswahl", "Bitte zuerst ein Quelldokument auswählen.")
                return
            source_id, filename, _, stored_text = records[index]
            # A text selection becomes the draft; otherwise the full currently edited text.
            selection = preview.textCursor().selectedText().replace("\\u2029", "\\n").strip()
            draft_text = selection or preview.toPlainText().strip()
            if not draft_text:
                QMessageBox.warning(dialog, "Keine Daten", "Der Dokumenttext ist leer.")
                return
            form_dialog = QDialog(dialog)
            form_dialog.setWindowTitle("Karriereeintrag aus Dokument — Entwurf")
            form_dialog.resize(760, 530)
            form = QFormLayout(form_dialog)
            kind = QComboBox()
            kind.addItems(KINDS)
            title = QLineEdit()
            title.setPlaceholderText("Berufsbezeichnung, Abschluss oder Zertifikat")
            org = QLineEdit()
            period = QLineEdit()
            details = QTextEdit()
            details.setPlainText(draft_text)
            form.addRow("Quelle", QLabel(f"{filename} (Dokument #{source_id})"))
            form.addRow("Kategorie", kind)
            form.addRow("Bezeichnung", title)
            form.addRow("Arbeitgeber / Institution", org)
            form.addRow("Zeitraum", period)
            form.addRow("Text aus Quelle", details)
            form.addRow(QLabel("Der Eintrag wird ungeprüft gespeichert und muss später bestätigt werden."))
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                       QDialogButtonBox.StandardButton.Cancel)
            form.addRow(buttons)
            def persist_draft():
                try:
                    save_entry(self.engine, kind.currentText(), title.text(), org.text(),
                               period.text(), details.toPlainText(), verified=False,
                               source_document_id=source_id)
                except ValueError as exc:
                    QMessageBox.warning(form_dialog, "Eingabe", str(exc))
                    return
                form_dialog.accept()
            buttons.accepted.connect(persist_draft)
            buttons.rejected.connect(form_dialog.reject)
            if form_dialog.exec() == QDialog.DialogCode.Accepted:
                status.setText("Karriereentwurf gespeichert. Unter Karriere-Daten prüfen und bestätigen.")

        upload.clicked.connect(upload_doc)
        edit.clicked.connect(save_text)
        transfer.clicked.connect(transfer_to_career)
        remove.clicked.connect(remove_doc)
        refresh_docs()
        dialog.exec()

    def snippets(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Textbaustein-Bibliothek")
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)
        items = QListWidget()
        entries = list_snippets(self.engine)
        for _, title, category, _ in entries:
            items.addItem(f"[{category}] {title}")
        layout.addWidget(items)
        title = QLineEdit()
        title.setPlaceholderText("Titel des neuen Textbausteins")
        category = QLineEdit()
        category.setPlaceholderText("Kategorie, z.B. IT, Management, Motivation")
        content = QTextEdit()
        content.setPlaceholderText("Formulierung eingeben ...")
        layout.addWidget(title)
        layout.addWidget(category)
        layout.addWidget(content)
        def show_selected(index):
            if index >= 0:
                _, t, c, body = entries[index]
                title.setText(t)
                category.setText(c)
                content.setPlainText(body)
        items.currentRowChanged.connect(show_selected)
        def save_new():
            try:
                save_snippet(self.engine, title.text(), category.text(), content.toPlainText())
                entries[:] = list_snippets(self.engine)
                items.clear()
                for _, t, c, _ in entries:
                    items.addItem(f"[{c}] {t}")
                title.clear()
                category.clear()
                content.clear()
            except ValueError as exc:
                QMessageBox.warning(dialog, "Eingabe", str(exc))
        def refresh_items():
            entries[:] = list_snippets(self.engine)
            items.clear()
            for _, t, c, _ in entries:
                items.addItem(f"[{c}] {t}")
        def save_existing():
            index = items.currentRow()
            if index < 0:
                QMessageBox.information(dialog, "Auswahl", "Bitte zuerst einen Textbaustein auswählen.")
                return
            try:
                update_snippet(self.engine, entries[index][0], title.text(), category.text(), content.toPlainText())
                refresh_items()
            except ValueError as exc:
                QMessageBox.warning(dialog, "Eingabe", str(exc))
        def remove_existing():
            index = items.currentRow()
            if index < 0:
                return
            if QMessageBox.question(dialog, "Löschen", "Diesen Textbaustein wirklich löschen?") != QMessageBox.StandardButton.Yes:
                return
            delete_snippet(self.engine, entries[index][0])
            refresh_items()
            title.clear()
            category.clear()
            content.clear()
        save_button = QPushButton("Als neuen Textbaustein speichern")
        save_button.clicked.connect(save_new)
        layout.addWidget(save_button)
        edit_button = QPushButton("Ausgewählten Baustein aktualisieren")
        edit_button.clicked.connect(save_existing)
        layout.addWidget(edit_button)
        delete_button = QPushButton("Ausgewählten Baustein löschen")
        delete_button.setObjectName("pink")
        delete_button.clicked.connect(remove_existing)
        layout.addWidget(delete_button)
        dialog.exec()

    def edit_profile(self):
        dialog = ProfileDialog(self.engine, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_profile(self.engine, dialog.skills.toPlainText(), dialog.experience.toPlainText())
            self.refresh()

    def new_job(self):
        dialog = JobDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                added = add_job(self.engine, dialog.title_input.text(), dialog.company.text(),
                                dialog.url.text(), dialog.description.toPlainText())
                if not added:
                    QMessageBox.information(self, "Dublettenprüfung", "Stelle bereits vorhanden.")
                self.refresh()
            except ValueError as exc:
                QMessageBox.warning(self, "Eingabefehler", str(exc))

    def mail_studio(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("JobHunter | Application Mailer")
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        screen = QApplication.primaryScreen().availableGeometry()
        dialog.resize(min(950, screen.width() - 80), min(780, screen.height() - 80))
        outer = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        panel = QWidget()
        scroll.setWidget(panel)
        layout = QVBoxLayout(panel)
        heading = QLabel("✉  APPLICATION MAILER")
        heading.setObjectName("hero")
        layout.addWidget(heading)
        settings = load_settings()
        config = QFormLayout()
        host = QLineEdit(str(settings.get("host", "")))
        port = QLineEdit(str(settings.get("port", 587)))
        security = QComboBox()
        security.addItems(["STARTTLS", "SSL/TLS"])
        security.setCurrentText(settings.get("security", "STARTTLS"))
        username = QLineEdit(settings.get("username", ""))
        sender = QLineEdit(settings.get("sender", ""))
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        password.setPlaceholderText("Leer lassen, um vorhandenes Passwort zu verwenden")
        signature = QTextEdit(settings.get("signature", ""))
        signature.setFixedHeight(85)
        config_fields = [host, port, security, username, sender, password, signature]
        for label, widget in [("SMTP-Host", host), ("Port", port), ("TLS-Modus", security),
                              ("Benutzername", username), ("Absender", sender),
                              ("SMTP-/App-Passwort", password), ("Signatur", signature)]:
            config.addRow(label, widget)
        layout.addLayout(config)
        def current_settings():
            return dict(host=host.text().strip(), port=port.text().strip(),
                        security=security.currentText(), username=username.text().strip(),
                        sender=sender.text().strip(), signature=signature.toPlainText())
        verified = bool(settings.get("verified", False))
        state = QLabel()
        state.setObjectName("subtitle")
        actions = QHBoxLayout()
        save_button = QPushButton("Verbindung prüfen und speichern")
        save_button.setObjectName("primary")
        edit_button = QPushButton("Einstellungen ändern")
        actions.addWidget(save_button)
        actions.addWidget(edit_button)
        layout.addLayout(actions)
        layout.addWidget(state)
        def lock_config(locked):
            for field in config_fields:
                field.setEnabled(not locked)
            save_button.setEnabled(not locked)
            edit_button.setEnabled(locked)
            state.setText("✓ SMTP geprüft und Einstellungen gesperrt" if locked
                          else "SMTP-Einstellungen bearbeiten und Verbindung prüfen")
        def store():
            try:
                cfg = current_settings()
                save_button.setEnabled(False)
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                try:
                    test_connection(cfg, password.text() or None)
                finally:
                    QApplication.restoreOverrideCursor()
                    save_button.setEnabled(True)
                cfg["verified"] = True
                save_settings(cfg, password.text() or None)
                password.clear()
                lock_config(True)
                QMessageBox.information(dialog, "SMTP geprüft", "TLS und Anmeldung erfolgreich. Einstellungen gespeichert und gesperrt.")
            except Exception as exc:
                QMessageBox.warning(dialog, "SMTP-Prüfung fehlgeschlagen", f"{type(exc).__name__}: {exc}")
        save_button.clicked.connect(store)
        edit_button.clicked.connect(lambda: lock_config(False))
        # A previous verified flag is not proof that the current account still works.
        lock_config(verified)
        layout.addWidget(QLabel("NACHRICHT  •  Vor dem Versand kontrollieren"))
        form = QFormLayout()
        recipient = QLineEdit()
        subject = QLineEdit()
        body = QTextEdit()
        body.setPlaceholderText("Nachricht eingeben ...")
        body.setMinimumHeight(145)
        form.addRow("An", recipient)
        form.addRow("Betreff", subject)
        form.addRow("Nachricht", body)
        layout.addLayout(form)
        attachments = QListWidget()
        attachments.setMinimumHeight(90)
        layout.addWidget(attachments)
        attachment_paths = []
        controls = QHBoxLayout()
        def attach():
            paths, _ = QFileDialog.getOpenFileNames(dialog, "Anhänge auswählen")
            for path in paths:
                if path not in attachment_paths:
                    attachment_paths.append(path)
                    attachments.addItem(Path(path).name)
        def detach():
            index = attachments.currentRow()
            if index >= 0:
                attachment_paths.pop(index)
                attachments.takeItem(index)
        for label, callback in [("＋ Anhänge auswählen", attach), ("Anhang entfernen", detach)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        def compose():
            text = body.toPlainText().rstrip()
            sig = signature.toPlainText().strip()
            return text + ("\\n\\n" + sig if sig else "")
        def send():
            from .mailer import build_message
            try:
                if not save_button.isEnabled() and not edit_button.isEnabled():
                    raise ValueError("SMTP-Konfiguration ist nicht bereit.")
                if not edit_button.isEnabled():
                    raise ValueError("Bitte SMTP-Einstellungen zuerst prüfen und speichern.")
                cfg = current_settings()
                build_message(cfg["sender"], recipient.text(), subject.text(), compose(), attachment_paths)
                summary = (f"Von: {cfg['sender']}\\nAn: {recipient.text()}\\n"
                           f"Betreff: {subject.text()}\\nAnhänge: "
                           f"{', '.join(Path(p).name for p in attachment_paths) or 'keine'}"
                           f"\\n\\n{compose()}")
                if QMessageBox.question(dialog, "Versand bestätigen", summary,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return
                send_button.setEnabled(False)
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                try:
                    send_mail(cfg, recipient.text(), subject.text(), compose(), attachment_paths)
                finally:
                    QApplication.restoreOverrideCursor()
                    send_button.setEnabled(True)
                log_mail(self.engine, recipient.text(), subject.text(), "sent")
                QMessageBox.information(dialog, "Versendet", "SMTP-Server hat die Nachricht angenommen.")
            except Exception as exc:
                log_mail(self.engine, recipient.text(), subject.text(), "failed", type(exc).__name__)
                QMessageBox.warning(dialog, "Versand fehlgeschlagen", f"{type(exc).__name__}: {exc}")
        send_button = QPushButton("✉ Nachricht prüfen und senden")
        send_button.setObjectName("primary")
        send_button.clicked.connect(send)
        outer.addWidget(send_button)
        layout.addWidget(QLabel("LETZTE VERSANDVERSUCHE"))
        logview = QListWidget()
        logview.setMinimumHeight(95)
        for date, to, subj, status in mail_history(self.engine):
            logview.addItem(f"{date[:19]}  |  {status.upper()}  |  {to}  |  {subj}")
        layout.addWidget(logview)
        dialog.exec()

    def rejected_jobs(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("JobHunter | Verworfene Stellen")
        dialog.resize(820, 530)
        layout = QVBoxLayout(dialog)
        heading = QLabel("◈  PAPIERKORB / VERWORFENE STELLEN")
        heading.setObjectName("hero")
        layout.addWidget(heading)
        layout.addWidget(QLabel("Verworfene Stellen bleiben gespeichert und können wiederhergestellt werden."))
        items = QListWidget()
        layout.addWidget(items)
        history = QTextEdit()
        history.setReadOnly(True)
        layout.addWidget(history)
        records = list_rejected(self.engine)
        for job_id, title, company, _ in records:
            items.addItem(f"#{job_id}  {title}  |  {company}")
        if not records:
            history.setPlainText("Keine verworfenen Stellen vorhanden.")
        def show_history(index):
            if index < 0 or index >= len(records):
                history.clear()
                return
            events = list_status_events(self.engine, records[index][0])
            history.setPlainText("\\n".join(
                f"{date}: {old} → {new}" for old, new, date in events
            ) or "Keine Statusänderungen protokolliert.")
        items.currentRowChanged.connect(show_history)
        def restore():
            index = items.currentRow()
            if index < 0 or index >= len(records):
                QMessageBox.information(dialog, "Auswahl", "Bitte eine Stelle auswählen.")
                return
            set_status(self.engine, records[index][0], "new")
            dialog.accept()
            self.refresh()
        button = QPushButton("↩ Ausgewählte Stelle wiederherstellen")
        button.setObjectName("primary")
        button.clicked.connect(restore)
        layout.addWidget(button)
        dialog.exec()

    def change_status(self, status):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Auswahl", "Bitte zuerst eine Stelle auswählen.")
            return
        job_id = int(self.table.item(row, 0).text())
        set_status(self.engine, job_id, status)
        self.refresh()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    icon_path = Path(__file__).resolve().parent.parent / 'jobhunter.ico'
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
