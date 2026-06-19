"""Source-adapter contract.

Adapters resolve an *origin* (local path/glob, URL, future object store) to a
list of ingestible sources. Format parsing is Docling's job (root ``spec.md``
§3.1); an adapter only answers "where do the bytes come from".

A ``Source`` is anything ``DoclingConverter.run(sources=...)`` accepts: a path
(``str``/``Path``) or an in-memory ``ByteStream``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from haystack.dataclasses import ByteStream

# What an adapter yields and the converter ingests.
Source = str | Path | ByteStream


@runtime_checkable
class SourceAdapter(Protocol):
    """Resolve a configured origin to a list of ingestible sources."""

    def discover(self) -> list[Source]:
        """Return the sources this origin currently exposes."""
        ...
