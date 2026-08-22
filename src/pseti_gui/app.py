import sys
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from pseti_gui.mainwin import MainWin

VER = f'V{version("pseti-gui")}'

app = typer.Typer(add_completion=False, no_args_is_help=False)


def _version_callback(value: bool) -> None:
    if value:
        print(f"pseti-gui {version('pseti-gui')}")
        raise typer.Exit()


@app.command()
def main(
    version_opt: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print the installed pseti-gui version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Launch the PANOSETI Control GUI."""
    qapp = QApplication(sys.argv)
    # Org/app name are required for QSettings() (used e.g. to remember the
    # last-opened data_config.json path) to resolve a persistent store.
    qapp.setOrganizationName("PANOSETI")
    qapp.setApplicationName("pseti-gui")
    icon_path = Path(__file__).resolve().parent / "figure" / "panoseti_icon.png"
    qapp.setWindowIcon(QIcon(str(icon_path)))
    w = MainWin()
    w.setWindowTitle(f"PANOSETI Control - {VER}")
    w.show()
    sys.exit(qapp.exec())


if __name__ == "__main__":
    app()
