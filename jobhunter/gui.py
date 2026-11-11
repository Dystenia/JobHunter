from __future__ import annotations
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QDialog,
    QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QMessageBox, QLabel)
from sqlalchemy.orm import Session
from .core import database, add_job, list_jobs, set_status, save_profile, Profile
from .theme import DARK_STYLESHEET

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
        self.setWindowTitle("JobHunter — Application Studio")
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
        for label, callback in [("Profil", self.edit_profile), ("Stelle hinzufügen", self.new_job),
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
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
