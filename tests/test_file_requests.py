import pytest

from pocketagent.core.file_requests import (
    FileRequest,
    FileRequestError,
    extract_file_requests,
    resolve_outbound_file,
    send_file_instructions,
)


def test_extract_no_block_returns_text_unchanged():
    cleaned, requests = extract_file_requests("just text")
    assert cleaned == "just text"
    assert requests == []


def test_extract_multiple_blocks_in_order():
    text = 'Here:\n\n```send-file\npath = "a.png"\n```\n\n```send-file\npath = "b.pdf"\n```'
    cleaned, requests = extract_file_requests(text)
    assert cleaned == "Here:"
    assert requests == [FileRequest(path="a.png"), FileRequest(path="b.pdf")]


def test_extract_block_missing_path_is_error():
    _, requests = extract_file_requests("```send-file\nname = \"x\"\n```")
    assert len(requests) == 1
    assert isinstance(requests[0], FileRequestError)


def test_extract_invalid_toml_is_error():
    _, requests = extract_file_requests("```send-file\npath = \n```")
    assert isinstance(requests[0], FileRequestError)


def test_resolve_relative_path_inside_workspace(tmp_path):
    (tmp_path / "img").mkdir()
    target = tmp_path / "img" / "a.png"
    target.write_bytes(b"x")
    assert resolve_outbound_file(tmp_path, "img/a.png", 100) == target.resolve()


def test_resolve_absolute_path_inside_workspace(tmp_path):
    target = tmp_path / "a.png"
    target.write_bytes(b"x")
    assert resolve_outbound_file(tmp_path, str(target), 100) == target.resolve()


def test_resolve_rejects_parent_escape(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (tmp_path / "secret.txt").write_text("s")
    with pytest.raises(ValueError, match="outside the workspace"):
        resolve_outbound_file(work, "../secret.txt", 100)


def test_resolve_rejects_absolute_path_outside_workspace(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("s")
    with pytest.raises(ValueError, match="outside the workspace"):
        resolve_outbound_file(work, str(secret), 100)


def test_resolve_rejects_symlink_pointing_outside(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("s")
    (work / "link.txt").symlink_to(secret)
    with pytest.raises(ValueError, match="outside the workspace"):
        resolve_outbound_file(work, "link.txt", 100)


def test_resolve_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError, match="doesn't exist"):
        resolve_outbound_file(tmp_path, "nope.png", 100)


def test_resolve_rejects_directory(tmp_path):
    (tmp_path / "d").mkdir()
    with pytest.raises(ValueError, match="isn't a regular file"):
        resolve_outbound_file(tmp_path, "d", 100)


def test_resolve_rejects_oversized_file(tmp_path):
    (tmp_path / "big.bin").write_bytes(b"x" * 101)
    with pytest.raises(ValueError, match="upload limit"):
        resolve_outbound_file(tmp_path, "big.bin", 100)


def test_resolve_missing_file_error_names_where_it_looked(tmp_path):
    with pytest.raises(ValueError) as exc_info:
        resolve_outbound_file(tmp_path, "sub/nope.png", 100)
    assert str((tmp_path / "sub" / "nope.png").resolve()) in str(exc_info.value)


def test_send_file_instructions_name_the_resolved_workspace(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    text = send_file_instructions(link)
    assert str(real) in text
    assert str(link) not in text
    assert "not your shell's current directory" in text
