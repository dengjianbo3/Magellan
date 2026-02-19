from pathlib import Path

from app.core.uploaded_file_locator import locate_uploaded_file


def test_locate_uploaded_file_prefers_exact_match(tmp_path):
    target = tmp_path / "abc-123.pdf"
    target.write_bytes(b"pdf")
    (tmp_path / "abc-123.pdf.bak").write_bytes(b"bak")

    found = locate_uploaded_file("abc-123.pdf", search_dirs=[str(tmp_path)])

    assert found == str(target)


def test_locate_uploaded_file_falls_back_to_prefix_match(tmp_path):
    target = tmp_path / "abc-123.pdf"
    target.write_bytes(b"pdf")

    found = locate_uploaded_file("abc-123", search_dirs=[str(tmp_path)])

    assert found == str(target)


def test_locate_uploaded_file_rejects_path_traversal(tmp_path):
    safe = tmp_path / "safe.pdf"
    safe.write_bytes(b"ok")

    found = locate_uploaded_file("../safe.pdf", search_dirs=[str(tmp_path)])

    assert found == str(safe)
    assert Path(found).name == "safe.pdf"


def test_locate_uploaded_file_returns_none_when_missing(tmp_path):
    found = locate_uploaded_file("missing.pdf", search_dirs=[str(tmp_path)])
    assert found is None
