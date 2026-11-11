from __future__ import annotations
import os
import struct
import sys
import tempfile
import winreg
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QLinearGradient
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "jobhunter.ico"

def create_icon():
    app = QApplication.instance() or QApplication([])
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = []
    for size in sizes:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#0C1024"))
        gradient.setColorAt(1, QColor("#322061"))
        p.setBrush(gradient)
        p.setPen(QColor("#00E5FF"))
        margin = max(1, size // 20)
        p.drawRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin, size * .22, size * .22)
        font = QFont("Segoe UI", max(7, round(size * .43)), QFont.Weight.Black)
        p.setFont(font)
        p.setPen(QColor("#00E5FF"))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "J")
        p.end()
        images.append((size, pix))
    # ICO with PNG-encoded images (Windows Vista and later)
    import io
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    blobs = []
    for size, pix in images:
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buffer, "PNG")
        buffer.close()
        blobs.append((size, bytes(data)))
    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    directory = bytearray()
    for size, data in blobs:
        directory.extend(struct.pack("<BBBBHHII", size if size < 256 else 0, size if size < 256 else 0, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    ICON.write_bytes(header + directory + b"".join(data for _, data in blobs))
    return ICON

def desktop_path():
    # Windows Shell known folder via SHGetKnownFolderPath, supports redirected desktops
    import ctypes
    from ctypes import wintypes
    from uuid import UUID
    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
    raw = UUID("B4BFCC3A-DB2C-424C-B029-7FE99A87C641").bytes_le
    guid = GUID.from_buffer_copy(raw)
    ptr = ctypes.c_wchar_p()
    result = ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(ptr))
    if result != 0:
        raise OSError(f"Desktop folder lookup failed: {result}")
    try:
        return Path(ptr.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(ptr, ctypes.c_void_p))

def main():
    if sys.platform != "win32":
        raise SystemExit("Dieses Setup ist nur fuer Windows vorgesehen.")
    pythonw = ROOT / ".venv" / "Scripts" / "pythonw.exe"
    if not pythonw.exists():
        raise SystemExit("Python-Umgebung fehlt. Zuerst .venv installieren.")
    icon = ICON if ICON.exists() else create_icon()
    desktop = desktop_path()
    desktop.mkdir(parents=True, exist_ok=True)
    link = desktop / "JobHunter.lnk"
    # Use Windows Script Host COM through PowerShell, no third-party dependencies
    import subprocess
    ps = (
        "$s = New-Object -ComObject WScript.Shell; "
        "$l = $s.CreateShortcut($env:JOBHUNTER_LINK); "
        "$l.TargetPath = $env:JOBHUNTER_PYTHONW; "
        "$l.Arguments = ([char]34) + $env:JOBHUNTER_MAIN + ([char]34); "
        "$l.WorkingDirectory = $env:JOBHUNTER_ROOT; "
        "$l.IconLocation = $env:JOBHUNTER_ICON; "
        "$l.Description = 'JobHunter Application Studio'; "
        "$l.Save()"
    )
    env = dict(os.environ, JOBHUNTER_LINK=str(link), JOBHUNTER_PYTHONW=str(pythonw),
               JOBHUNTER_MAIN=str(ROOT / "main.py"), JOBHUNTER_ROOT=str(ROOT),
               JOBHUNTER_ICON=str(icon))
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                   env=env, check=True)
    print(f"Icon: {icon}")
    print(f"Desktop-Verknuepfung: {link}")

if __name__ == "__main__":
    main()
