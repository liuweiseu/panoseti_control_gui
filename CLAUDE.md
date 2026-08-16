# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

`pseti-gui` — a PyQt6 desktop GUI for controlling a PANOSETI observatory (power, DAQ, MAROC/mask config,
calibration) and live-viewing detector images. It is a thin control-panel front end over two sibling repos:
[`panoseti`](../panoseti) (every control button shells out to the `pseti` CLI resolved on `PATH` — see
Architecture) and [`panoseti_grpc`](../panoseti_grpc) (the `AioDaqDataClient` used to stream images, imported
directly as a dependency). `pseti-gui` itself carries no reference to where either sibling repo's source
lives — it only needs `pseti` on `PATH` and `configs/grpc_config.json` pointed at the right JSON files.

## Common Commands

```bash
uv sync                  # install dependencies into .venv
uv run pseti-gui         # run from inside the repo
uv tool install .        # install as a standalone `pseti-gui` command
```

There are no automated tests or CI in this repo — verify changes by running the GUI.

## Configuration

Only one config file left, and it doesn't point at a `panoseti` source checkout:

- **`configs/grpc_config.json`** — read by `grpc_process.py` (default arg, `start_grpc_clicked` doesn't
  override it) for the *image-streaming* backend only: `daq_config_path`, `net_config_path`, `hp_io_cfg_path`.
  These must point at real `daq_config.json`/`network_config.json`/`hp_io_config*.json` files (typically
  inside a `panoseti/control/configs/` checkout, but `pseti-gui` doesn't care where) — see
  [panoseti's config system](../panoseti/CLAUDE.md#configuration-system) for what those files mean.

There used to also be a `configs/panoseti_config.json` for a `verbose` flag gating whether
`grpc_process.py`'s captured stdout/stderr got printed — removed; `grpc_stdout`/`grpc_stderr` in
`mainwin.py` now print unconditionally, so `MainWin.__init__` takes no config-path argument at all.

**Prerequisite, not a config file:** the `pseti` CLI itself must be installed and resolvable on the `PATH`
of whatever environment launches `pseti-gui` — see Architecture for `uv tool install --editable` and the
`PanoPaths` caveat.

## Architecture

### Two-process, two-IPC-channel design

The GUI process (`MainWin`) never talks gRPC directly. Instead:

1. **Control actions** — every button (`power_on_clicked`, `marocconfig_clicked`, `getuid_clicked`,
   `startdaq_clicked`/`stopdaq_clicked`, redis/reboot/calibration, etc.) goes through `run_pseti(*args)`,
   which invokes the `pseti` CLI **by name on `PATH`** via `QProcess` (`pseti power on`, `pseti cfg
   maroc-config`, `pseti uids`, `pseti start`, `pseti stop`, …) — see the `panoseti/control` CLI reference
   for the full subcommand list. Stdout/stderr stream into the console log pane
   (`ps_stdout`/`ps_stderr`/`append_log`). This deliberately does **not** go through any interpreter path
   configured in `pseti-gui`: `pseti` must be installed as a standalone tool so `pseti-gui` doesn't need to
   know where the `panoseti` checkout or its interpreter live — only that `pseti` resolves on `PATH`.
   **Caveat:** the `control` package's `PanoPaths.software_root_dir()` locates the observatory config/state
   tree from the installed package's own `__file__`, not from an env var by default — a non-editable
   `uv tool install` copies the package into an isolated tool venv, so it would silently resolve configs
   from *that* venv instead of the real checkout. Use `uv tool install --editable <path-to-panoseti>/control`
   (keeps `__file__` pointing at the live checkout) or set `PSETI_ROOT`/`PSETI_CONFIG` in the environment
   `pseti-gui` launches from.
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
PTI, 252 = Fern, 253 = Winter, 254 = Gattini) rather than derived from `obs_config.json` (see the
`# TODO: improve this part` comment) — there's no `obs_config.json` path wired into `pseti-gui` to derive it
from even if that TODO were done. When adding a new site/module, update `telescope_info` here.

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

`open_data_config()` lazily creates one `DataConfigWin` (`QMainWindow` with a `File > Open...` action,
`self.action_open`) + one `DataConfigOp` (all the get/set logic + `load_config()`/`collect_config()`) and
reuses both on subsequent opens — `DataConfigOp.__init__` wires signals exactly once; don't reconstruct it
per-open, or `on_open_clicked`/`on_ok_clicked`/etc. end up connected multiple times on the same long-lived
`win.ui` widgets and fire once per prior open. There is no default/hardcoded source file: `DataConfigOp.src_config`
starts `None`, and `on_open_clicked()` (wired to `action_open.triggered`) pops a `QFileDialog` to pick a
`data_config.json` to load; `collect_config()` (on clicking OK) writes back to whatever path is currently in
the `config_output_dir` line-edit field (populated by `load_config()`, but also directly user-editable).
`DataConfigOp` is deliberately just get/set pairs per widget plus two translation functions — see
[panoseti's data_config.json constraints](../panoseti/CLAUDE.md#data-config-validation-constraints) for what
values are actually valid before wiring up a new field.

## Logging

Uses the project-standard `panoseti_grpc.telemetry.logger.get_logger(service_name, log_dir=...)` — the same
factory documented in [panoseti's control CLAUDE.md](../panoseti/control/CLAUDE.md#telemetry--logging).
Each component gets its own logger under the `pseti_gui.*` namespace (`pseti_gui.mainwin`,
`pseti_gui.grpc_process`, `pseti_gui.data_config_gen`), writing to `/var/log/panoseti/<hostname>/{service}.log`
+ `.jsonl` plus a Rich console handler; falls back to a temp dir if `/var/log/panoseti` isn't writable by the
current user. `grpc_process.py`'s own stdout/stderr is additionally captured by the *parent* process via
`QProcess` and unconditionally `print()`-ed to the terminal `pseti-gui` was launched from
(`grpc_stdout`/`grpc_stderr` in `mainwin.py`).
