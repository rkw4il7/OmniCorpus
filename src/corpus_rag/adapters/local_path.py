"""Local filesystem source adapter.

Resolves a configured ``root`` to a sorted list of file paths. ``root`` may be:
- a glob pattern (contains ``*``/``?``/``[``), expanded with recursive ``**``; or
- a directory, in which case every file beneath it is discovered; or
- a single file path.

Directories matched by a glob are dropped — only files are handed to the
converter. Order is deterministic (sorted) for reproducible ingestion.
"""

from __future__ import annotations

import glob
from pathlib import Path

from corpus_rag.adapters.base import Source

_GLOB_CHARS = ("*", "?", "[")


class LocalPathAdapter:
    """Discover local files under a path, directory, or glob ``root``."""

    def __init__(self, root: str) -> None:
        if not root:
            raise ValueError("local_path adapter requires a non-empty 'root'")
        self.root = root

    def discover(self) -> list[Source]:
        if any(ch in self.root for ch in _GLOB_CHARS):
            matches = glob.glob(self.root, recursive=True)
            paths = [Path(m) for m in matches]
        else:
            p = Path(self.root)
            if p.is_dir():
                paths = list(p.rglob("*"))
            else:
                paths = [p]
        files = sorted(str(p) for p in paths if Path(p).is_file())
        return list(files)
