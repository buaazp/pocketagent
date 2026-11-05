"""Lets an agent send files (images, PDFs, ...) back into the chat as real
attachments, by including a fenced block anywhere in its reply:

    ```send-file
    path = "images/slicker-brush.jpg"
    ```

`path` is resolved against the conversation's workspace dir (an absolute
path is accepted too), and must end up inside that dir after following
symlinks -- so an agent can only ever post files from its own channel's
workspace, never arbitrary files elsewhere on the machine. One block per
file; several blocks send several files.

Engine (core/engine.py) strips these blocks out of the reply text, sends the
text as usual, then hands the resolved paths to Platform.send_files. Only
platforms with `supports_files = True` get send_file_instructions() appended
to the system prompt; on any other platform a block is reported back as an
error note instead.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_SEND_FILE_BLOCK_RE = re.compile(r"```send-file\s*\n(.*?)```", re.DOTALL)

_SEND_FILE_INSTRUCTIONS_TEMPLATE = """\
You can send a file from this conversation's workspace, {work_dir} (an \
image, PDF, chart, etc.), to the user as a real chat attachment with a \
fenced code block anywhere in your reply:
```send-file
path = "{work_dir}/relative/path/to/file.png"
```
Prefer an absolute path. A relative `path` is resolved against the workspace \
above, not your shell's current directory, so it doesn't follow `cd` or any \
change to your working directory. Files outside the workspace are refused. \
To share something from the web, download it into the workspace first. Use \
one block per file. Each block is removed from what the user sees and the \
file is attached after your message, so don't describe this syntax to them."""


def send_file_instructions(work_dir: str | Path) -> str:
    """System-prompt text teaching the send-file convention for `work_dir`.

    Names the workspace explicitly because that's what paths are resolved
    against (see resolve_outbound_file), and the agent's own working
    directory can drift away from it mid-session.
    """

    return _SEND_FILE_INSTRUCTIONS_TEMPLATE.format(work_dir=Path(work_dir).resolve())


@dataclass
class FileRequest:
    path: str


@dataclass
class FileRequestError:
    detail: str


def extract_file_requests(text: str) -> tuple[str, list[FileRequest | FileRequestError]]:
    """Strip ```send-file``` blocks out of `text`.

    Returns the cleaned text and one FileRequest -- or FileRequestError, if
    a block was malformed -- per block found, in the order they appeared.
    """

    requests: list[FileRequest | FileRequestError] = []

    def _consume(match: re.Match[str]) -> str:
        requests.append(_parse_send_file_block(match.group(1)))
        return ""

    cleaned = _SEND_FILE_BLOCK_RE.sub(_consume, text).strip()
    return cleaned, requests


def resolve_outbound_file(work_dir: str | Path, path: str, max_bytes: int) -> Path:
    """Resolve `path` against `work_dir` and check it's safe to send.

    Raises ValueError (with a user-facing message) if the file is outside
    work_dir, missing, not a regular file, or larger than max_bytes.
    """

    root = Path(work_dir).resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"'{path}' is outside the workspace")
    if not resolved.exists():
        raise ValueError(f"'{path}' doesn't exist (looked for {resolved})")
    if not resolved.is_file():
        raise ValueError(f"'{path}' isn't a regular file")
    size = resolved.stat().st_size
    if size > max_bytes:
        raise ValueError(
            f"'{path}' is {size / 1024 / 1024:.1f} MB, over the "
            f"{max_bytes / 1024 / 1024:.0f} MB upload limit"
        )
    return resolved


def _parse_send_file_block(body: str) -> FileRequest | FileRequestError:
    try:
        data = tomllib.loads(body)
    except tomllib.TOMLDecodeError as exc:
        return FileRequestError(f"invalid send-file block ({exc})")

    path = data.get("path")
    if not isinstance(path, str) or not path:
        return FileRequestError("send-file block needs a 'path' as a string")

    return FileRequest(path=path)
