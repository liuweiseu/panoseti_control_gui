# uv 打包 + pseti-gui 命令行入口 设计文档

日期：2026-08-15

## 背景

`panoseti_control_gui` 目前用一堆仓库相对路径来定位资源（`configs/`、`figure/`、`src/grpc_process.py`），靠 `main.py` 里的 `os.chdir(__file__ 所在目录)` 撑住。项目希望改为用 `uv` 管理依赖，并且能通过 `uv tool install` 装成一个全局命令 `pseti-gui`。

`uv tool install` 会把包装进一个独立的隔离 venv，生成的命令运行时的工作目录是用户调用时所在的任意目录，不再是仓库目录。因此当前"相对于脚本所在目录找资源"的写法在被打包安装后会失效，需要针对这一点做结构调整。

## 范围（本次要做的）

- 让 `uv sync` / `uv run pseti-gui`（开发）和 `uv tool install .` / 全局 `pseti-gui`（安装后）都能正常启动主窗口
- 图标、占位图等**包自带静态资源**不再依赖运行目录，无论从哪里启动都能找到
- 启动 gRPC 数据采集子进程的方式（`start_grpc_clicked` 里拉起 `src/grpc_process.py`）改为不依赖仓库路径的模块调用方式——这是本仓库自身的模块，必须现在修，否则打包后核心功能（开始采集）直接不可用
- 清理明确无用的代码（`src/worker.py` 死代码）
- README 更新为 uv 工作流

## 明确不做的（本次范围外，后续单独处理）

- `configs/panoseti_config.json` 的查找方式（用户按部署环境编辑的站点路径、python 路径等）——保持现有的"当前工作目录下 `configs/panoseti_config.json`，找不到则打日志警告"的行为不动
- `power.py`/`config.py` 等 panoseti_sw 里的外部脚本调用方式——保持现状，等这些脚本本身也迁移成 uv tool 时再一起处理
- 日志文件位置（`utils.make_rich_logger` 写到 cwd 下的 `./logs/`）——保持不动
- 上一轮已经处理过的 `panoseti_grpc` 子模块删除、`hp_io_cfg_path` 路径失效问题——不在本次范围内

这些都是"部署环境相关、且当前代码已经能优雅降级（缺失时报警告而不是崩溃）"的部分，刻意不在这次深改，避免范围膨胀。

## 设计

### 1. 目录结构：改成 src-layout 包

```
src/
  pseti_gui/
    __init__.py
    app.py            # main() 入口逻辑（原 main.py 的内容）
    mainwin.py
    mainwin_ui.py
    data_config_win.py
    data_config_ui.py
    grpc_process.py
    grpc_thread.py
    utils.py          # 原 utils/utils.py 并入
    figure/
      panoseti_icon.png
      placeholder.png
      mainwin_gui.png
      data_config_gui.png
```

- 删除顶层 `utils/` 目录（内容并入 `src/pseti_gui/utils.py`）
- `figure/*.png` 移入 `src/pseti_gui/figure/`，作为包内资源随 wheel 一起打包
- `ui/*.ui`（Qt Designer 源文件）留在仓库根目录不动，仅用于开发时 `pyuic6` 重新生成 `*_ui.py`，不参与打包
- 删除 `src/worker.py`（未被任何地方 import 的原型/死代码，上一轮 review 已确认）
- 相应更新 import：
  - `from src.mainwin import MainWin` → `from pseti_gui.mainwin import MainWin`
  - `from src.data_config_ui import Ui_Form` → `from pseti_gui.data_config_ui import Ui_Form`
  - `from utils.utils import make_rich_logger` → `from pseti_gui.utils import make_rich_logger`
  - 影响文件：`mainwin.py`、`data_config_win.py`、`grpc_process.py`、`grpc_thread.py`

### 2. 入口文件

有两个同名但不同层级的 `app.py`，职责不同：

- `src/pseti_gui/app.py`（包内，新增）：真正的入口逻辑，内容基本是现在根目录 `main.py` 的代码，但窗口图标路径改成包内相对路径（例如 `Path(__file__).parent / "figure" / "panoseti_icon.png"`），不再依赖 `os.chdir` 之后的 cwd。`[project.scripts]` 指向的就是这里的 `main()`
- 根目录 `app.py`（**由 `main.py` 改名而来**，不是新文件）：只是一个薄壳，方便在仓库目录内直接 `python app.py` / `uv run app.py`：
  ```python
  from pseti_gui.app import main

  if __name__ == "__main__":
      main()
  ```

`panoseti_control.sh` 直接删除，不保留。

### 3. gRPC 子进程启动方式

`mainwin.py::start_grpc_clicked` 现状：
```python
program = 'python'
args = ['-u', 'src/grpc_process.py', '-m', 'ph256']
self.grpc_process.start(program, args)
```

改为模块调用，不依赖仓库相对路径：
```python
program = sys.executable
args = ['-u', '-m', 'pseti_gui.grpc_process', '-m', 'ph256']
self.grpc_process.start(program, args)
```

`grpc_process.py` 的 `if __name__ == '__main__':` 部分不用改，只是现在通过 `-m pseti_gui.grpc_process` 触发。

### 4. uv / pyproject.toml

新增仓库根目录 `pyproject.toml`：

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

- 用 `uv sync` 生成并提交 `uv.lock`
- `.gitignore` 补充 `.venv/`（目前没有这条，仓库里已经有一个未提交的 `.venv`）

### 5. README 更新

- Get Started 换成：
  - 开发：`uv sync`，然后 `uv run pseti-gui`（或 `uv run app.py`，两者等价）
  - 安装为全局命令：`uv tool install .`
- 删掉旧的 `pip install pyqt6/pyqtgraph/rich`、`pip install -r .../requirements.txt` 段落（改由 uv 依赖管理统一处理）
- 保留 Linux 下 `libxcb-cursor0` 的系统库提示（这个跟 uv/pip 无关，仍然需要）

## 测试计划

1. `uv sync` 成功，生成 `uv.lock`
2. `uv run pseti-gui`：在仓库目录内启动，确认主窗口能正常弹出、图标/占位图正常显示
3. `uv tool install .`：安装为全局命令后，**从仓库外的目录**（如 `/tmp`）执行 `pseti-gui`，确认：
   - 窗口能正常弹出，图标/占位图正常显示（验证不再依赖 cwd）
   - `configs/panoseti_config.json` 找不到时按预期打印警告日志而不是崩溃（验证范围外的部分没有被意外破坏）
4. 检查 `import pseti_gui.grpc_process` 可用（不实际起 gRPC 连接，只验证模块可导入、路径正确）

## 已知遗留问题（不在本次修复范围）

- `src/mainwin.py`/`configs/grpc_config.json` 里的 `hp_io_cfg_path` 仍指向已删除的 `panoseti_grpc/` 子模块路径，会在实际点击"start grpc"时报 `FileNotFoundError`（上一轮已记录，用户后续自行处理）
- `configs/panoseti_config.json`、日志目录、`power.py` 等外部脚本的调用方式仍然是 cwd 相对的，全局安装后除非在含 `configs/` 的目录下运行，否则相关功能不可用——这是本次明确排除的范围，后续等这些脚本本身也迁移到 uv tool 管理时一起处理
