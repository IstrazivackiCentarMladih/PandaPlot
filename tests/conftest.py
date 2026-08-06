import os

# Must run before any PySide6/QApplication import so Qt never opens a real window.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
