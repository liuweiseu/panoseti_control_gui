from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

# Note: PSETI_GUI_ prefix (not PSETI_GRPC_) deliberately -- PSETI_GRPC_* is
# already used by the panoseti_grpc package's own server-side config env
# vars (PSETI_GRPC_DAQ_CONFIG, PSETI_GRPC_NETWORK_CONFIG, PSETI_GRPC_ENV_FILE)
# and this is an unrelated, pseti-gui-side client setting.
_ENV_VAR = "PSETI_GUI_GRPC_CONFIG_FILE"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "grpc_config.json"


@dataclass(frozen=True)
class GrpcConfig:
    host: str
    port: int
    path: Path


def _resolve_config_path() -> Path:
    env_path = os.getenv(_ENV_VAR)
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_PATH


def load_grpc_config() -> GrpcConfig:
    """Load the host/port grpc_process connects to when launched from the GUI.

    Path resolution: `PSETI_GUI_GRPC_CONFIG_FILE` env var if set, otherwise
    the package's bundled default (localhost:50051).
    """
    path = _resolve_config_path()
    with open(path) as f:
        raw = json.load(f)

    host = str(raw["host"])
    port = int(raw["port"])
    if not (0 < port < 65536):
        raise ValueError(f"{path}: port must be between 1 and 65535 (got {port})")

    return GrpcConfig(host=host, port=port, path=path)
