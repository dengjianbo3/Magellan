"""
Utilities for locating uploaded files from shared storage.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional


_DEFAULT_SHARED_UPLOAD_DIR = os.getenv("REPORT_ORCH_SHARED_UPLOAD_DIR", "/var/uploads")
_LEGACY_LOCAL_UPLOAD_DIR = (
    Path(__file__).resolve().parents[1] / "uploads"
).as_posix()


def _iter_search_dirs(search_dirs: Optional[Iterable[str]] = None) -> list[str]:
    if search_dirs is not None:
        return [d for d in search_dirs if d]
    return [_DEFAULT_SHARED_UPLOAD_DIR, _LEGACY_LOCAL_UPLOAD_DIR]


def locate_uploaded_file(file_id: str, search_dirs: Optional[Iterable[str]] = None) -> Optional[str]:
    """
    Locate an uploaded file by file_id.

    Strategy:
    1. Exact filename match in each search directory.
    2. Prefix match as compatibility fallback.
    """
    if not file_id:
        return None

    safe_file_id = os.path.basename(file_id.strip())
    if not safe_file_id:
        return None

    for directory in _iter_search_dirs(search_dirs):
        if not os.path.isdir(directory):
            continue

        exact_path = os.path.join(directory, safe_file_id)
        if os.path.isfile(exact_path):
            return exact_path

    for directory in _iter_search_dirs(search_dirs):
        if not os.path.isdir(directory):
            continue

        try:
            for filename in os.listdir(directory):
                if filename.startswith(safe_file_id):
                    path = os.path.join(directory, filename)
                    if os.path.isfile(path):
                        return path
        except OSError:
            continue

    return None
