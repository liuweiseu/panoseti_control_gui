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
        },
        "verbose": false
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

