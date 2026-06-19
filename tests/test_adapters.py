"""Tests for the source-adapter registry and local/url adapters.

Offline: the URL adapter's network call is patched; local discovery runs
against a real ``tmp_path`` tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_rag.adapters import (
    LocalPathAdapter,
    UrlAdapter,
    build_adapter,
    discover_all,
)
from corpus_rag.adapters import url as url_mod
from corpus_rag.settings import SourceConfig

# --- LocalPathAdapter ----------------------------------------------------


@pytest.fixture
def corpus_tree(tmp_path: Path) -> Path:
    (tmp_path / "a.pdf").write_text("a")
    (tmp_path / "b.html").write_text("b")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.docx").write_text("c")
    return tmp_path


def test_local_glob_discovers_files_recursively(corpus_tree: Path) -> None:
    adapter = LocalPathAdapter(root=str(corpus_tree / "**" / "*"))
    found = adapter.discover()
    assert {Path(f).name for f in found} == {"a.pdf", "b.html", "c.docx"}


def test_local_directory_root_walks_tree(corpus_tree: Path) -> None:
    adapter = LocalPathAdapter(root=str(corpus_tree))
    found = adapter.discover()
    assert sorted(Path(f).name for f in found) == ["a.pdf", "b.html", "c.docx"]


def test_local_single_file_root(corpus_tree: Path) -> None:
    target = corpus_tree / "a.pdf"
    assert LocalPathAdapter(root=str(target)).discover() == [str(target)]


def test_local_discovery_is_sorted_deterministic(corpus_tree: Path) -> None:
    adapter = LocalPathAdapter(root=str(corpus_tree / "**" / "*"))
    assert adapter.discover() == adapter.discover() == sorted(adapter.discover())


def test_local_excludes_directories(corpus_tree: Path) -> None:
    found = LocalPathAdapter(root=str(corpus_tree / "*")).discover()
    assert all(Path(f).is_file() for f in found)
    assert str(corpus_tree / "sub") not in found


def test_local_empty_root_raises() -> None:
    with pytest.raises(ValueError, match="non-empty 'root'"):
        LocalPathAdapter(root="")


# --- UrlAdapter ----------------------------------------------------------


class _FakeResp:
    def __init__(self, data: bytes, content_type: str) -> None:
        self._data = data
        self.headers = _FakeHeaders(content_type)

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakeHeaders:
    def __init__(self, content_type: str) -> None:
        self._ct = content_type

    def get_content_type(self) -> str:
        return self._ct


def test_url_adapter_returns_bytestream_with_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(url: str, timeout: int = 0) -> _FakeResp:
        return _FakeResp(b"<html>hi</html>", "text/html")

    monkeypatch.setattr(url_mod.urllib.request, "urlopen", _fake_urlopen)

    streams = UrlAdapter(url="http://example.com/doc.html").discover()
    assert len(streams) == 1
    stream = streams[0]
    assert stream.data == b"<html>hi</html>"
    assert stream.mime_type == "text/html"
    assert stream.meta["source_url"] == "http://example.com/doc.html"


def test_url_adapter_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="non-empty 'url'"):
        UrlAdapter(url="")


# --- Registry ------------------------------------------------------------


def test_build_adapter_local(corpus_tree: Path) -> None:
    cfg = SourceConfig(adapter="local_path", root=str(corpus_tree))
    assert isinstance(build_adapter(cfg), LocalPathAdapter)


def test_build_adapter_url() -> None:
    cfg = SourceConfig(adapter="url", url="http://example.com/x")
    assert isinstance(build_adapter(cfg), UrlAdapter)


def test_build_adapter_unknown_raises() -> None:
    cfg = SourceConfig(adapter="ftp", root="x")
    with pytest.raises(ValueError, match="Unknown source adapter 'ftp'"):
        build_adapter(cfg)


def test_discover_all_flattens_multiple_sources(corpus_tree: Path) -> None:
    configs = [
        SourceConfig(adapter="local_path", root=str(corpus_tree / "a.pdf")),
        SourceConfig(adapter="local_path", root=str(corpus_tree / "b.html")),
    ]
    found = discover_all(configs)
    assert sorted(Path(f).name for f in found) == ["a.pdf", "b.html"]
