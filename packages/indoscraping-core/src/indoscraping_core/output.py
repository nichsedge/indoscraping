from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


def _atomic_write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def write_json(path: str, data: Any, *, indent: int = 2) -> None:
    _atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=indent))


def meta_sidecar_path(output_json_path: str) -> str:
    if output_json_path.endswith(".json"):
        return output_json_path[:-5] + ".meta.json"
    return output_json_path + ".meta.json"


def write_latest_and_history(
    *,
    latest_path: str,
    history_path: Optional[str],
    payload: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Write output with safe atomic replace.

    Keeps the primary JSON payload schema unchanged (usually list[dict]).
    Optional `meta` is written to a sidecar JSON next to latest_path.
    """

    write_json(latest_path, payload)

    if history_path:
        write_json(history_path, payload)

    if meta is not None:
        write_json(meta_sidecar_path(latest_path), meta)
