from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QDialog,
    QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QMessageBox, QLabel, QFileDialog, QListWidget, QComboBox, QCheckBox)
from PySide6.QtGui import QIcon
from sqlalchemy.orm import Session
from .core import database, add_job, list_jobs, set_status, save_profile, Profile
from .theme import DARK_STYLESHEET
from .career import CareerDocument, TextSnippet, extract_document, save_document, list_documents, save_snippet, list_snippets, update_snippet, delete_snippet, update_document, delete_document
from .core import Base
from .entries import CareerEntry, KINDS, entries, save_entry, remove_entry

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
        self.engine = database()
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
        for label, callback in [("Profil", self.edit_profile), ("Karriere-Daten", self.career_entries), ("CV importieren", self.import_cv), ("Dokumentenarchiv", self.documents), ("Textbausteine", self.snippets), ("Stelle hinzufügen", self.new_job),
                                ("In Warteschlange", lambda: self.change_status("queued")),
                                ("Beworben", lambda: self.change_status("applied")),
                                ("Verwerfen", lambda: self.change_status("rejected")),
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
        remove = QPushButton("Dokument löschen")
        remove.setObjectName("pink")
        actions.addWidget(upload)
        actions.addWidget(edit)
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
        upload.clicked.connect(upload_doc)
        edit.clicked.connect(save_text)
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
