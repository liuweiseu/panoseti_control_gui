import sys, os
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QIcon

from src.mainwin import MainWin

VER = 'V0.0.3'

def main():
    basedir = Path(__file__).resolve().parent
    os.chdir(basedir)
    app = QApplication(sys.argv)
    script_path = os.path.realpath(__file__)
    curdir = os.path.dirname(script_path)
    app.setWindowIcon(QIcon(f"{curdir}/figure/panoseti_icon.png"))
    w = MainWin()
    w.setWindowTitle(f"PANOSETI Control - {VER}")
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
    