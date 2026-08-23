# PANOSETI CONTROL GUI
This GUI is based on [panoseti software](https://github.com/panoseti/panoseti) and the [panoseti-grpc](https://pypi.org/project/panoseti-grpc/) package.  
![MAINWIN_GUI](./figure/mainwin_gui.png)  

<img src="./figure/data_config_gui.png" width="400">

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
4. install the `pseti` CLI (from the [panoseti](https://github.com/panoseti/panoseti) repo's `control/` package) as a
   standalone tool, so it's on your `PATH` — the power/DAQ/config buttons in the GUI shell out to it by name:
    ```
    uv tool install --editable /path/to/panoseti/control
    ```
    Use `--editable` so the installed `pseti` keeps resolving its config/state directories from your actual
    `panoseti` checkout (see [CLAUDE.md](CLAUDE.md) for why).
5. (optional) customize the image-window grid  
    `pseti-gui` shows a fixed 2x2 grid (PTI/Fern/Winter/Gattini) out of the box, sized to fill the display
    area with square cells. To change the grid size or which module shows where, generate a template and
    edit it:
    ```
    pseti-gui --config-template   # writes ./window_config.json
    ```
    then point `pseti-gui` at your copy:
    ```
    export PSETI_WINDOW_CONFIG_FILE=/path/to/window_config.json
    ```
6. (optional) point the image-streaming backend at a non-default `panoseti_grpc` server  
    The "Start Visualization" button always connects to `localhost:50051`. To stream from elsewhere — an
    edge DAQ node, or a headnode/gateway that fans in multiple edge nodes server-side — run
    `python -m pseti_gui.grpc_process --host <host> --port <port> --mode <mode>` directly instead of using
    the button (`--mode` is one of `mov8`/`mov16`/`ph256`/`ph1024`, default `ph1024`).
    The stream must already be initialized (e.g. via `pseti start`, or a server with
    `init_from_default = true`) — this GUI only attaches to it.
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
Run `pseti-gui -h` (or `--help`) to see all CLI options, including `--version`, `--config-template` (see
step 5 above), and shell completion (`--install-completion`/`--show-completion`, same as `pseti`/`pseti-grpc`).

Once the image-streaming backend ("Start Visualization" button) is running, its stdout/stderr are printed
directly to the terminal `pseti-gui` was launched from; every window shows a zero-valued image until its
module's first real frame arrives, and reverts to the default placeholder image on "Stop Visualization".

The Data Config window (Configs > Data Config) remembers the last file you opened across GUI restarts, and
asks for confirmation naming the exact target file before writing it.

