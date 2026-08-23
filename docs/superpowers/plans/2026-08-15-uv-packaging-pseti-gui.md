# uv Packaging + pseti-gui CLI Entry Point Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `panoseti_control_gui` into an installable `pseti_gui` package managed by `uv`, exposing a `pseti-gui` console-script entry point that works correctly whether run via `uv run` inside the repo or installed globally via `uv tool install .` and launched from any directory.

**Architecture:** Move the application code from loose `src/`/`utils/`/`main.py` modules into a proper `src/pseti_gui/` package. Runtime-loaded static assets (app icon, placeholder image) move inside the package and are addressed via `Path(__file__).parent`-relative paths instead of cwd-relative paths, so they resolve correctly regardless of where the installed command is invoked from. The gRPC data-acquisition subprocess, which is launched by the GUI itself (not an external deployment script), is switched from a repo-relative file path to a `-m pseti_gui.grpc_process` module invocation using `sys.executable`, so it keeps working after installation. A new `pyproject.toml` (hatchling backend) declares the package, its dependencies, and the `pseti-gui = "pseti_gui.app:main"` console script.

**Tech Stack:** Python, PyQt6, pyqtgraph, uv, hatchling

**Spec:** `docs/superpowers/specs/2026-08-15-uv-packaging-design.md`

## Global Constraints

- `requires-python = ">=3.14"` (per spec section 4)
- Distribution name `pseti-gui`, import package name `pseti_gui`, console script `pseti-gui = "pseti_gui.app:main"`
- Build backend: `hatchling` (`[tool.hatch.build.targets.wheel] packages = ["src/pseti_gui"]`)
- Root entry file is named `app.py` (renamed from `main.py`, not a new file); the package's own entry module is a separate file also named `app.py`, living at `src/pseti_gui/app.py`
- Do **not** change: `configs/panoseti_config.json` lookup behavior (stays cwd-relative, missing file → warning log, not an error), how `power.py`/`config.py`/other `panoseti_sw` scripts are invoked, or the `logs/` directory location (`./logs`, cwd-relative). These are explicitly out of scope per the spec.
- Do **not** fix the already-known `hp_io_cfg_path` dangling reference (tracked separately, out of scope per spec)
- `figure/mainwin_gui.png` and `figure/data_config_gui.png` are README-only screenshots, not runtime resources — they stay in the root-level `figure/` directory, unlike `panoseti_icon.png`/`placeholder.png` which move into the package

---

### Task 1: Restructure into `src/pseti_gui` package

**Files:**
- Create: `src/pseti_gui/__init__.py`
- Move: `src/mainwin.py` → `src/pseti_gui/mainwin.py` (edited)
- Move: `src/mainwin_ui.py` → `src/pseti_gui/mainwin_ui.py` (unchanged)
- Move: `src/data_config_win.py` → `src/pseti_gui/data_config_win.py` (edited)
- Move: `src/data_config_ui.py` → `src/pseti_gui/data_config_ui.py` (unchanged)
- Move: `src/grpc_process.py` → `src/pseti_gui/grpc_process.py` (edited)
- Move: `src/grpc_thread.py` → `src/pseti_gui/grpc_thread.py` (unchanged content)
- Move: `utils/utils.py` → `src/pseti_gui/utils.py` (unchanged content)
- Move: `figure/panoseti_icon.png` → `src/pseti_gui/figure/panoseti_icon.png`
- Move: `figure/placeholder.png` → `src/pseti_gui/figure/placeholder.png`
- Delete: `src/worker.py` (dead prototype file, not imported anywhere — confirmed via `git grep -n worker` returning no hits outside itself)
- Delete: `utils/` (now empty)

**Interfaces:**
- Produces: importable package `pseti_gui` with `pseti_gui.mainwin.MainWin`, `pseti_gui.mainwin_ui.Ui_MainWindow`, `pseti_gui.data_config_win.DataConfigWin`/`DataConfigOp`, `pseti_gui.data_config_ui.Ui_Form`, `pseti_gui.grpc_process.DaqDataBackend`/`run(args)`, `pseti_gui.grpc_thread.AsyncioThread`, `pseti_gui.utils.make_rich_logger`/`create_logger`, and package-relative assets at `pseti_gui/figure/panoseti_icon.png` / `pseti_gui/figure/placeholder.png`.
- Consumed by: Task 2 (builds `pseti_gui/app.py` on top of `pseti_gui.mainwin.MainWin`) and Task 3 (`uv sync`/`uv run` needs this package to exist and be import-clean).

- [ ] **Step 1: Move the files with `git mv` (preserves history)**

```bash
mkdir -p src/pseti_gui/figure
touch src/pseti_gui/__init__.py
git add src/pseti_gui/__init__.py

git mv src/mainwin.py src/pseti_gui/mainwin.py
git mv src/mainwin_ui.py src/pseti_gui/mainwin_ui.py
git mv src/data_config_win.py src/pseti_gui/data_config_win.py
git mv src/data_config_ui.py src/pseti_gui/data_config_ui.py
git mv src/grpc_process.py src/pseti_gui/grpc_process.py
git mv src/grpc_thread.py src/pseti_gui/grpc_thread.py
git mv utils/utils.py src/pseti_gui/utils.py
git mv figure/panoseti_icon.png src/pseti_gui/figure/panoseti_icon.png
git mv figure/placeholder.png src/pseti_gui/figure/placeholder.png

git rm src/worker.py
rmdir utils
```

- [ ] **Step 2: Fix imports and add `FIGURE_DIR` in `src/pseti_gui/mainwin.py`**

Replace the import block at the top of the file:

```python
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QSocketNotifier

import logging, json, os, sys
from pathlib import Path
import pyqtgraph as pg
import numpy as np
import socket

from pseti_gui.mainwin_ui import Ui_MainWindow
from pseti_gui.data_config_win import DataConfigWin, DataConfigOp
import asyncio, signal
from multiprocessing import shared_memory, resource_tracker

from pseti_gui.grpc_thread import AsyncioThread

from pseti_gui.utils import make_rich_logger

NUM_PLOTS = 4

SOCK_PATH = "/tmp/panoseti_meta.sock"
FIGURE_DIR = Path(__file__).resolve().parent / "figure"
```

(This is the same block as before, with `from src.` → `from pseti_gui.`, `from utils.utils import` → `from pseti_gui.utils import`, `sys` added to the `os` import line since it's now needed for `sys.executable` in Step 4, and a new `FIGURE_DIR` constant.)

Then fix the hardcoded placeholder image path — find:

```python
        pixmap = QPixmap("figure/placeholder.png")
```

Replace with:

```python
        pixmap = QPixmap(str(FIGURE_DIR / "placeholder.png"))
```

- [ ] **Step 3: Fix imports in `src/pseti_gui/data_config_win.py`**

Replace the top of the file:

```python
from PyQt6.QtWidgets import QDialog, QWidget
from pseti_gui.data_config_ui import Ui_Form

import logging
import json
from pathlib import Path
from pseti_gui.utils import make_rich_logger
```

(Drops the stale `#from data_config_win import Ui_DataConfigWin` comment, `from src.data_config_ui` → `from pseti_gui.data_config_ui`, `from utils.utils import` → `from pseti_gui.utils import`.)

- [ ] **Step 4: Fix imports in `src/pseti_gui/grpc_process.py`**

Find:

```python
from daq_data.client import AioDaqDataClient
import signal

sys.path.insert(0, 'utils')
from utils import make_rich_logger
```

Replace with:

```python
from daq_data.client import AioDaqDataClient
import signal

from pseti_gui.utils import make_rich_logger
```

- [ ] **Step 5: Verify no old-style imports remain and files compile**

```bash
grep -rn "from src\.\|from utils\.\|sys\.path\.insert" src/pseti_gui/
```

Expected: no output (empty).

```bash
python3 -m py_compile src/pseti_gui/*.py
echo "exit: $?"
```

Expected: `exit: 0` (this only checks syntax — it will pass even though PyQt6 isn't installed in the ambient interpreter; real import verification happens in Task 3 once `uv sync` has installed dependencies).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: restructure src/ and utils/ into installable pseti_gui package

Moves the application modules into src/pseti_gui/ (src-layout), merges
utils/utils.py into the package, moves the two runtime-loaded images
(app icon, placeholder) inside the package so they resolve via
Path(__file__)-relative paths instead of cwd-relative ones, and drops
the dead src/worker.py prototype. Import statements updated accordingly.
EOF
)"
```

---

### Task 2: Rename `main.py` → `app.py`, add package entry point, fix gRPC subprocess launch

**Files:**
- Create: `src/pseti_gui/app.py`
- Move: `main.py` → `app.py` (rewritten as a thin shell)
- Modify: `src/pseti_gui/mainwin.py:start_grpc_clicked` (subprocess launch)
- Delete: `panoseti_control.sh`

**Interfaces:**
- Consumes: `pseti_gui.mainwin.MainWin` (Task 1)
- Produces: `pseti_gui.app.main()` — the function `[project.scripts]` will point to in Task 3

- [ ] **Step 1: Create `src/pseti_gui/app.py`**

```python
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
```

Note what's deliberately **not** here compared to the old `main.py`: no `os.chdir(basedir)` and no `os.path.realpath`/`curdir` dance. The icon is now found via the package's own location, not cwd, so the chdir is unnecessary — and removing it is required to keep `configs/panoseti_config.json` lookups (in `MainWin.__init__`, out of scope for this plan) resolving relative to wherever the user actually invoked `pseti-gui` from, rather than being silently redirected into the installed package directory.

- [ ] **Step 2: Rename `main.py` to `app.py` at the repo root**

```bash
git mv main.py app.py
```

Then replace its entire contents with:

```python
from pseti_gui.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Fix the gRPC subprocess launch in `src/pseti_gui/mainwin.py`**

Find:

```python
    def start_grpc_clicked(self, mode='ph256'):
        self.logger.info('Start PANOSETI gPRC process.')
        self.grpc_process_exit = False
        program = 'python'
        args = ['-u', 'src/grpc_process.py', '-m', 'ph256']
        self.grpc_process.start(program, args)
```

Replace with:

```python
    def start_grpc_clicked(self, mode='ph256'):
        self.logger.info('Start PANOSETI gPRC process.')
        self.grpc_process_exit = False
        program = sys.executable
        args = ['-u', '-m', 'pseti_gui.grpc_process', '-m', 'ph256']
        self.grpc_process.start(program, args)
```

(`sys` is already imported as of Task 1 Step 2.)

- [ ] **Step 4: Delete `panoseti_control.sh`**

```bash
git rm panoseti_control.sh
```

- [ ] **Step 5: Verify**

```bash
python3 -m py_compile app.py src/pseti_gui/app.py src/pseti_gui/mainwin.py
echo "exit: $?"
```

Expected: `exit: 0`

```bash
grep -n "os.chdir\|src/grpc_process.py\|panoseti_control.sh" app.py src/pseti_gui/app.py src/pseti_gui/mainwin.py
```

Expected: no output (empty) — confirms the chdir call and the old repo-relative subprocess path are both gone.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: rename main.py to app.py, add package entry point

Root app.py (renamed from main.py) is now a thin shell around
pseti_gui.app:main, which is what uv's [project.scripts] entry will
point to in the next task. Also switches the gRPC subprocess launch
from a repo-relative script path to `sys.executable -m
pseti_gui.grpc_process`, since that path breaks once the app is
installed outside the repo. Drops panoseti_control.sh, superseded by
`uv run pseti-gui` / the installed `pseti-gui` command.
EOF
)"
```

---

### Task 3: Add `pyproject.toml`, run `uv sync`, verify the package actually imports and builds

**Files:**
- Create: `pyproject.toml`
- Modify: `.gitignore`
- Create (generated): `uv.lock`

**Interfaces:**
- Consumes: the `pseti_gui` package produced by Tasks 1–2 (`src/pseti_gui/__init__.py` must exist for the hatchling wheel target to build)
- Produces: a working `uv sync`-managed `.venv` with all runtime dependencies installed, and a `pseti-gui` script resolvable via `uv run pseti-gui`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "pseti-gui"
version = "0.0.3"
requires-python = ">=3.14"
dependencies = [
    "pyqt6",
    "pyqtgraph",
    "rich",
    "numpy",
    "panoseti-grpc",
]

[project.scripts]
pseti-gui = "pseti_gui.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pseti_gui"]
```

- [ ] **Step 2: Add `.venv/` to `.gitignore`**

Current `.gitignore`:

```
data_config_gen.log
daq_data/*
**/__pycache__/*
logs/*
```

Append `.venv/` as a new line, so the file reads:

```
data_config_gen.log
daq_data/*
**/__pycache__/*
logs/*
.venv/
```

- [ ] **Step 3: Run `uv sync`**

```bash
uv sync
echo "exit: $?"
```

Expected: `exit: 0`, and `uv.lock` is created/updated in the repo root. If dependency resolution fails, read the error — it most likely means a version constraint conflict between `panoseti-grpc`'s own dependency floors and something else; do not loosen `requires-python` below `3.14` to work around it without checking with the user first, since that's a value fixed by the spec.

- [ ] **Step 4: Verify the package actually imports with real dependencies present**

```bash
uv run python -c "
import pseti_gui
import pseti_gui.app
import pseti_gui.mainwin
import pseti_gui.data_config_win
import pseti_gui.grpc_process
import pseti_gui.grpc_thread
import pseti_gui.utils
print('OK')
"
```

Expected: prints `OK` with no traceback. This is the real regression check for Task 1's import rewrite — `py_compile` only caught syntax errors, this catches wrong module paths.

- [ ] **Step 5: Verify the console script resolves and the packaged image assets are included in the wheel**

```bash
uv run python -c "from pseti_gui.app import main; print(main)"
```

Expected: prints something like `<function main at 0x...>` — confirms `pseti_gui.app:main` (the target of `[project.scripts]`) is a real, importable callable.

```bash
uv build
unzip -l dist/*.whl | grep -E "panoseti_icon.png|placeholder.png"
```

Expected: both files listed inside the wheel under `pseti_gui/figure/`. If they're missing, hatchling's default git-tracked-file inclusion didn't pick them up — check that `git add` was run for the moved `.png` files in Task 1 (untracked files are excluded by hatchling's default VCS-based file selection).

- [ ] **Step 6: Try actually running the GUI from inside the repo**

```bash
uv run pseti-gui &
sleep 2
ps aux | grep -i "[p]seti-gui\|pseti_gui.app"
```

Expected: a running process is listed (the window process didn't crash/exit within 2 seconds). If a display is available, also visually confirm the main window and its icon appear normally, then close it. If it exited immediately, capture the traceback by running `uv run pseti-gui` in the foreground instead and read the error.

```bash
kill %1 2>/dev/null || true
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock .gitignore
git commit -m "$(cat <<'EOF'
build: add pyproject.toml, manage the project with uv

Declares pseti-gui as a hatchling-backed package with its runtime
dependencies (pyqt6, pyqtgraph, rich, numpy, panoseti-grpc) and a
pseti-gui console script pointing at pseti_gui.app:main. uv.lock is
generated by `uv sync` and committed so installs are reproducible.
EOF
)"
```

---

### Task 4: Verify `uv tool install` from outside the repo, update README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the working `uv sync`/`uv build` setup from Task 3

- [ ] **Step 1: Install as a global tool and run it from outside the repo**

```bash
uv tool install .
cd /tmp
pseti-gui &
sleep 2
ps aux | grep -i "[p]seti-gui\|pseti_gui.app"
```

Expected: process is running — this is the actual point of the whole exercise: the command works from a directory that has no `configs/`, `figure/`, or `src/` at all, because the icon/placeholder now resolve via the package's own location rather than cwd.

Also check the log output (or stderr if run in the foreground) does **not** show a crash — a `WARNING: panoseti_sw_path doesn't exist` / `"configs/panoseti_config.json" doesn't exist!` message in the log is expected and fine (that's the existing, intentionally-unchanged graceful-degradation behavior for the out-of-scope config lookup); an unhandled traceback is not.

```bash
kill %1 2>/dev/null || true
cd -
uv tool uninstall pseti-gui
```

(Uninstall again after the check so the machine doesn't end up with a stale globally-installed copy from this verification pass — the user can reinstall properly whenever they're ready to actually use it.)

- [ ] **Step 2: Update `README.md`**

Replace the project description line:

```markdown
This GUI is based on [panoseti software](https://github.com/panoseti/panoseti) and the [panoseti-grpc](https://pypi.org/project/panoseti-grpc/) package.  
```

(unchanged from the earlier submodule-removal edit — just confirming it's still correct.)

Replace the entire `# Get Started` through `# Start GUI` section with:

```markdown
# Get Started
1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. clone the repository
    ```
    git clone https://github.com/liuweiseu/panoseti_control_gui.git
    cd panoseti_control_gui
    ```
3. install dependencies
    ```
    uv sync
    ```
    **Note:** On Linux, PyQt6 may need an extra system library
    ```
    sudo apt update
    sudo apt install libxcb-cursor0
    ```
4. set the config file  
    You need to set the `configs/panoseti_config.json`:  
    ```
    {
        "panoseti_sw": {
            "sw_path": "/home/test/panoseti",
            "python_path": "/home/test/miniconda3/envs/py39/bin/python"
        },
        "pyqt": {
            "python_path": "/home/test/miniconda3/envs/grpc/bin/python"
        }
    }   
    ```
# Start GUI
There are two ways to start the GUI:
1. run it inside the repo with uv
    ```
    uv run pseti-gui
    ```
2. install it as a standalone command, then run it from anywhere
    ```
    uv tool install .
    pseti-gui
    ```
```

- [ ] **Step 3: Verify**

```bash
grep -n "submodule\|panoseti_control.sh\|conda create\|pip install\|python main.py" README.md
```

Expected: no output (empty) — confirms no stale references to the removed submodule workflow, the deleted shell script, the old conda/pip install steps, or the renamed `main.py`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: update README for uv-based install and run workflow

Replaces the conda/pip Get Started steps with `uv sync`, and documents
both `uv run pseti-gui` (repo-local) and `uv tool install .` (global
command) as ways to start the GUI.
EOF
)"
```
