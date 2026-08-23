import shutil
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from pseti_gui.mainwin import MainWin
from pseti_gui.window_config import DEFAULT_CONFIG_PATH

VER = f'V{version("pseti-gui")}'

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version_callback(value: bool) -> None:
    if value:
        print(f"pseti-gui {version('pseti-gui')}")
        raise typer.Exit()


def _config_template_callback(value: bool) -> None:
    if not value:
        return
    dest = Path.cwd() / DEFAULT_CONFIG_PATH.name
    if dest.exists():
        print(f"Refusing to overwrite existing file: {dest}")
        raise typer.Exit(code=1)
    shutil.copyfile(DEFAULT_CONFIG_PATH, dest)
    print(f"Wrote default window config template to {dest}")
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
    config_template_opt: Annotated[
        bool,
        typer.Option(
            "--config-template",
            help=(
                "Generate a window_config.json template in the current directory. "
                "Edit it to customize the image-window grid, then point the "
                "PSETI_WINDOW_CONFIG_FILE env var at it before launching pseti-gui."
            ),
            callback=_config_template_callback,
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
