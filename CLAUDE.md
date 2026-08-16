# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

`pseti-gui` — a PyQt6 desktop GUI for controlling a PANOSETI observatory (power, DAQ, MAROC/mask config,
calibration) and live-viewing detector images. It is a thin control-panel front end over two sibling repos
that must be installed alongside it: [`panoseti`](../panoseti) (the `control/` CLI scripts, invoked as
subprocesses) and [`panoseti_grpc`](../panoseti_grpc) (the `AioDaqDataClient` used to stream images).

## Common Commands

```bash
uv sync                  # install dependencies into .venv
uv run pseti-gui         # run from inside the repo
uv tool install .        # install as a standalone `pseti-gui` command
```

There are no automated tests or CI in this repo — verify changes by running the GUI.

## Configuration

`configs/panoseti_config.json` (git-ignored path values, but the file itself must exist) points the GUI at
the sibling `panoseti` checkout and its Python interpreter:

```json
{
    "panoseti_sw": {"sw_path": "/path/to/panoseti", "python_path": "/path/to/python"},
    "pyqt": {"python_path": "/path/to/python"},
    "verbose": false
}
```

`MainWin.__init__` (`src/pseti_gui/mainwin.py`) derives `daq_config.json`/`network_config.json`/
`obs_config.json`/`data_config.json` paths from `panoseti_sw.sw_path` + `/control/configs/...` — see
[panoseti's config system](../panoseti/CLAUDE.md#configuration-system) for what those files mean.
`hp_io_cfg_path` is currently hardcoded in `mainwin.py` to
`panoseti_grpc/daq_data/config/hp_io_config_palomar.json` (there's a commented-out `_simulate.json`
alternative right above it for local testing without hardware).

## Architecture

### Two-process, two-IPC-channel design

The GUI process (`MainWin`) never talks gRPC directly. Instead:

1. **Control actions** (`power_on_clicked`, `startdaq_clicked`, `marocconfig_clicked`, etc. in `mainwin.py`)
   shell out via `QProcess` to `panoseti_sw.python_path` running scripts in `<sw_path>/control/`
   (`power.py`, `config.py`, `start.py`, `stop.py`, `get_uids.py`). Stdout/stderr are streamed into the
   console log pane (`ps_stdout`/`ps_stderr`/`append_log`).
2. **Image streaming** runs in a separate child process (`start_grpc_clicked` launches
   `python -m pseti_gui.grpc_process` via `QProcess`) because `AioDaqDataClient` is asyncio-based and the
   main window runs the Qt event loop. This child process (`grpc_process.py`'s `DaqDataBackend`) owns the
   `AioDaqDataClient`, writes each incoming frame into a `multiprocessing.shared_memory.SharedMemory` block,
   and notifies the GUI process over a Unix domain socket at `/tmp/panoseti_meta.sock`.

### IPC protocol over the UDS socket

`MainWin` binds `/tmp/panoseti_meta.sock` as a server in `__init__` and registers a `QSocketNotifier` on its
fd (`_on_new_connection` / `_on_ready_read`) — no polling, no threads. `DaqDataBackend` connects as a client
and sends two kinds of newline-delimited JSON messages via `send_metadata()`:

- **Handshake** (`send_shm_info()`): `{"shm": name, "shape": [h, w], "mode": mode}` — the GUI opens the same
  shared-memory block (`create=False`) and wraps it in a same-shape/dtype `np.ndarray` view.
- **Per-frame** (`send_images()` loop): everything from `parsed_pano_image` except `image_array` (which
  lives in shared memory, not JSON) — e.g. `module_id`, `frame_number`. The GUI reads the current shared-memory
  contents into `data['image_array']` and calls `plot_data()`.

Both sides call `resource_tracker.unregister(shm._name, 'shared_memory')` — required because Python's
`resource_tracker` otherwise tries to unlink the block a second time when the *creating* process (`grpc_process`)
exits, racing the GUI process that still holds it open. `stop_grpc_clicked()` in `mainwin.py` is the only place
that actually calls `shm.unlink()`, guarded by `try/except` since the child process may already be gone.

Shutdown is `SIGINT`-driven, not a clean RPC: `stop_grpc_clicked()` sends `SIGINT` to the child's PID
(`self.grpc_process.processId()`), which `grpc_process.py`'s `signal.signal(SIGINT, handler)` turns into
`sys.exit(0)`; `MainWin.closeEvent` calls `stop_grpc_clicked()` if the child is still alive.

### Telescope/module mapping

`MainWin.telescope_info` maps `module_id` → `{display_name: [grid_row, grid_col]}` for the 2×2 image grid
(`NUM_PLOTS = 4`, `show_plot()`/`plot_data()`). This is currently **hardcoded** in `__init__` (module 250 =
PTI, 252 = Fern, 253 = Winter, 254 = Gattini) rather than derived from `obs_config.json` — `_parse_obs_config()`
exists but is unused (see the `# TODO: improve this part` comment). When adding a new site/module, update
`telescope_info` here, not `obs_config.json` alone.

### UI files: regenerate, don't hand-edit

`src/pseti_gui/mainwin_ui.py` and `data_config_ui.py` are generated from `ui/mainwin.ui` and
`ui/data_config_widget.ui` via `pyuic6` — both files carry a `# WARNING: ... will be lost when pyuic6 is run
again` header. Edit the `.ui` file (Qt Designer) and regenerate, e.g.:

```bash
uv run pyuic6 ui/mainwin.ui -o src/pseti_gui/mainwin_ui.py
uv run pyuic6 ui/data_config_widget.ui -o src/pseti_gui/data_config_ui.py
```

`Ui_MainWindow`/`Ui_Form` are then used as mixins/composition (`MainWin(QMainWindow, Ui_MainWindow)`,
`DataConfigWin.ui = Ui_Form()`) — widget attributes referenced in `mainwin.py`/`data_config_win.py`
(e.g. `self.power_on`, `self.ui.ph_mode_enable`) come from `setupUi()` and only exist after it runs.

### Data config sub-window

`open_data_config()` opens `DataConfigWin` (pure Qt widget wrapper) paired with `DataConfigOp` (all the
get/set logic + `load_config()`/`collect_config()`), which round-trips `<sw_path>/control/configs/data_config.json`
against the form fields. `DataConfigOp` is deliberately just get/set pairs per widget plus two translation
functions — see [panoseti's data_config.json constraints](../panoseti/CLAUDE.md#data-config-validation-constraints)
for what values are actually valid before wiring up a new field.

## Logging

`utils.make_rich_logger(name, clevel, flevel, mode)` sets up per-component loggers (`mainwin.log`,
`grpc_process.log`, `data_config_gen.log`) that write to `./logs/{name}_{date}.log` (full detail) plus a
Rich console handler (level `clevel`, default WARNING in this codebase — console output is intentionally
sparse). `grpc_process.py`'s own stdout is captured by the *parent* process via `QProcess` and only printed
if `verbose: true` in `panoseti_config.json`.
