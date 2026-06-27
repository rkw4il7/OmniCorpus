"""Tests for the Streamlit app's pure helpers.

Only import-safe, side-effect-free logic is unit-tested here; the Streamlit
rendering path is exercised manually / via the live acceptance run.
"""

from __future__ import annotations

from haystack import Document

from corpus_rag.app import (
    _FIRST_LINE_MAX,
    ALLOWED_UPLOAD_TYPES,
    _rank_score,
    _source_title,
    first_line,
)


def test_first_line_takes_first_nonempty_line() -> None:
    assert first_line("Preface\nThis guide...") == "Preface"


def test_first_line_strips_leading_blank_lines() -> None:
    assert first_line("\n\n  Title here \nbody") == "Title here"


def test_first_line_truncates_long_line() -> None:
    line = "x" * 200
    out = first_line(line)
    assert len(out) == _FIRST_LINE_MAX
    assert out.endswith("…")


def test_first_line_truncates_at_whitespace_boundary() -> None:
    # Space lands exactly at the slice point (index max_len-2): rstrip drops it,
    # so the result is strictly shorter than max_len.
    line = "x" * (_FIRST_LINE_MAX - 2) + " trailing" + "y" * 80
    out = first_line(line)
    assert len(out) < _FIRST_LINE_MAX  # rstrip consumed the boundary space
    assert out.endswith("…")
    assert not out[:-1].endswith(" ")


def test_first_line_keeps_short_line_verbatim() -> None:
    assert first_line("short") == "short"


def test_first_line_empty_content() -> None:
    assert first_line("") == ""
    assert first_line("   \n  ") == ""


def test_allowed_upload_types_are_bare_lowercase_extensions() -> None:
    # Streamlit file_uploader wants extensions without a leading dot.
    assert {"pdf", "docx", "html"} <= set(ALLOWED_UPLOAD_TYPES)
    assert all(t == t.lower() and not t.startswith(".") for t in ALLOWED_UPLOAD_TYPES)


def test_unload_document_deletes_chunks_and_removes_file(monkeypatch, tmp_path) -> None:
    """The only data-deletion path: DELETE by display name + remove the upload."""
    import psycopg

    from corpus_rag import app
    from corpus_rag import settings as settings_mod

    # Anchor uploads at a temp dir and seed the persisted file to be removed.
    monkeypatch.setattr(app, "UPLOAD_DIR", tmp_path)
    upload = tmp_path / "report.pdf"
    upload.write_bytes(b"pdf-bytes")

    captured: dict = {}

    class _FakeCursor:
        rowcount = 3

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql, params=None):
            captured["sql"] = sql
            captured["params"] = params
            return _FakeCursor()

    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: _FakeConn())
    monkeypatch.setattr(
        settings_mod,
        "get_settings",
        lambda: type("S", (), {"pg_conn_str": "postgresql://x"})(),
    )

    removed = app._unload_document("report.pdf")

    assert removed == 3
    assert "DELETE FROM haystack_documents" in captured["sql"]
    # Deletion keys on the SAME name expression the sidebar list shows.
    assert app._SOURCE_NAME_SQL in captured["sql"]
    assert captured["params"] == ("report.pdf",)
    assert not upload.exists()  # persisted upload removed too


def test_source_title_prefers_origin_filename() -> None:
    doc = Document(content="body", meta={"dl_meta": {"origin": {"filename": "guideline.pdf"}}})
    assert _source_title(doc) == "guideline.pdf"


def test_source_title_falls_back_to_heading_then_first_line() -> None:
    # No filename → most-specific heading.
    doc = Document(content="body", meta={"dl_meta": {"headings": ["Hand Hygiene"]}})
    assert _source_title(doc) == "Hand Hygiene"
    # No filename or heading → first line of the chunk.
    doc = Document(content="Vital Signs\nmore text", meta={})
    assert _source_title(doc) == "Vital Signs"


def test_source_title_never_blank() -> None:
    assert _source_title(Document(content="", meta={})) == "Untitled"


def test_rank_score_formats_rank_and_score() -> None:
    assert _rank_score(1, 0.9942) == "1 / 0.9942"
    assert _rank_score(2, 0.99417) == "2 / 0.9942"  # rounded to 4 dp
    assert _rank_score(3, None) == "3 / n/a"
