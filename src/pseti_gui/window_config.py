from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_ENV_VAR = "PSETI_GUI_WINDOW_CONFIG"
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "window_config.json"


@dataclass(frozen=True)
class WindowSlot:
    title: str
    row: int
    col: int


@dataclass(frozen=True)
class WindowConfig:
    rows: int
    cols: int
    # module_id -> WindowSlot
    slots: dict[int, WindowSlot]
    path: Path


def _resolve_config_path() -> Path:
    env_path = os.getenv(_ENV_VAR)
    if env_path:
        return Path(env_path)
    return _DEFAULT_CONFIG_PATH


def load_window_config() -> WindowConfig:
    """Load the image-window grid layout (dimensions + per-module title/position).

    Path resolution: `PSETI_GUI_WINDOW_CONFIG` env var if set, otherwise the
    package's bundled default (today's 2x2 PTI/Fern/Winter/Gattini layout).
    """
    path = _resolve_config_path()
    with open(path) as f:
        raw = json.load(f)

    rows = int(raw["rows"])
    cols = int(raw["cols"])
    if rows < 1 or cols < 1:
        raise ValueError(f"{path}: rows/cols must be >= 1 (got rows={rows}, cols={cols})")

    slots: dict[int, WindowSlot] = {}
    seen_positions: dict[tuple[int, int], int] = {}
    for entry in raw["windows"]:
        module_id = int(entry["module_id"])
        row = int(entry["row"])
        col = int(entry["col"])
        title = str(entry["title"])

        if not (0 <= row < rows and 0 <= col < cols):
            raise ValueError(
                f"{path}: window {title!r} (module_id={module_id}) has position "
                f"(row={row}, col={col}) outside the {rows}x{cols} grid"
            )
        if module_id in slots:
            raise ValueError(f"{path}: module_id {module_id} is listed more than once")
        position = (row, col)
        if position in seen_positions:
            raise ValueError(
                f"{path}: position {position} is used by both module_id "
                f"{seen_positions[position]} and {module_id}"
            )
        seen_positions[position] = module_id
        slots[module_id] = WindowSlot(title=title, row=row, col=col)

    return WindowConfig(rows=rows, cols=cols, slots=slots, path=path)
