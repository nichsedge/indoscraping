from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LineageMeta:
    run_id: str
    scraper_id: str
    started_at_utc: str
    python: str
    platform: str
    hostname: str
    user: str | None
    git_sha: str | None
    git_branch: str | None
    repo_dirty: bool | None


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_run(cmd: list[str], cwd: str | None = None) -> str | None:
    try:
        out = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.DEVNULL, text=True).strip()
        return out or None
    except Exception:
        return None


def collect_lineage(scraper_id: str, repo_root: str | None = None) -> Dict[str, Any]:
    """Collect runtime metadata for lineage/debugging.

    - Side-effect free
    - Does not raise if git is unavailable
    """

    repo_root = repo_root or os.getcwd()

    sha = _safe_run(["git", "rev-parse", "HEAD"], cwd=repo_root)
    branch = _safe_run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)

    dirty: bool | None
    try:
        status = _safe_run(["git", "status", "--porcelain"], cwd=repo_root)
        dirty = bool(status)
    except Exception:
        dirty = None

    meta = LineageMeta(
        run_id=str(uuid.uuid4()),
        scraper_id=scraper_id,
        started_at_utc=_iso_utc_now(),
        python=sys.version.split()[0],
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        hostname=socket.gethostname(),
        user=os.environ.get("USER") or os.environ.get("USERNAME"),
        git_sha=sha,
        git_branch=branch,
        repo_dirty=dirty,
    )
    return asdict(meta)
