import sys
from importlib.metadata import version
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from pseti_gui.mainwin import MainWin

VER = f'V{version("pseti-gui")}'


def main():
    app = QApplication(sys.argv)
    # Org/app name are required for QSettings() (used e.g. to remember the
    # last-opened data_config.json path) to resolve a persistent store.
    app.setOrganizationName("PANOSETI")
    app.setApplicationName("pseti-gui")
    icon_path = Path(__file__).resolve().parent / "figure" / "panoseti_icon.png"
    app.setWindowIcon(QIcon(str(icon_path)))
    w = MainWin()
    w.setWindowTitle(f"PANOSETI Control - {VER}")
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
