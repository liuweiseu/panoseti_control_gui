import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from pseti_gui.mainwin import MainWin

VER = 'V0.0.3'


def main():
    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "figure" / "panoseti_icon.png"
    app.setWindowIcon(QIcon(str(icon_path)))
    w = MainWin()
    w.setWindowTitle(f"PANOSETI Control - {VER}")
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
