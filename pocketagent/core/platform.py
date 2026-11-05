"""Platform abstraction: a messaging surface (Discord, Slack, Telegram, ...)."""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncContextManager, Awaitable, Callable

from .types import Message

MessageHandler = Callable[["Platform", Message], Awaitable[None]]


@contextlib.asynccontextmanager
async def _no_typing():
    yield


class Platform(ABC):
    """A messaging platform that delivers incoming messages and sends replies."""

    name: str

    # Whether send_files() is implemented. Engine only teaches the agent the
    # ```send-file``` convention (core/file_requests.py) on platforms that
    # set this, and refuses such blocks elsewhere.
    supports_files: bool = False
    # Largest single file send_files() accepts; checked by Engine before
    # calling it so an oversized file gets a clear note instead of an API error.
    max_upload_bytes: int = 10 * 1024 * 1024

    @abstractmethod
    async def start(self, handler: MessageHandler) -> None:
        """Connect to the platform and begin dispatching messages to handler."""

    @abstractmethod
    async def reply(self, reply_ctx: Any, content: str) -> None:
        """Reply to the message that produced reply_ctx."""

    @abstractmethod
    async def send(self, reply_ctx: Any, content: str) -> None:
        """Send a new (non-reply) message into the same channel as reply_ctx."""

    async def send_files(self, reply_ctx: Any, paths: list[Path]) -> None:
        """Send local files as attachments into the same channel as reply_ctx.

        Default: unsupported. Platforms that can upload attachments set
        supports_files = True and override this.
        """
        raise NotImplementedError(f"{self.name}: sending files not supported")

    @abstractmethod
    async def stop(self) -> None:
        """Disconnect from the platform."""

    def typing(self, reply_ctx: Any) -> AsyncContextManager[None]:
        """Show a "working" indicator for the duration of the returned block.

        Default: no-op. Platforms with a native typing indicator (e.g.
        Discord) override this; others can ignore it.
        """
        return _no_typing()

    async def make_channel_ctx(self, channel_id: str) -> Any:
        """Build a reply_ctx usable with reply()/send()/typing() for
        channel_id, with no triggering inbound message -- used by scheduled
        tasks (see core/scheduled_tasks.py) that proactively post into a
        channel rather than responding to one.

        Default: unsupported. Platforms that can address a channel directly
        (e.g. Discord) override this.
        """
        raise NotImplementedError(f"{self.name}: proactive channel sends not supported")


def allow_list(allow_from: str, user_id: str) -> bool:
    """Check whether user_id is permitted based on a comma-separated allow_from string.

    Empty or "*" means allow all. Comparison is case-insensitive.
    """
    allow_from = allow_from.strip()
    if allow_from == "" or allow_from == "*":
        return True
    return any(
        part.strip().lower() == user_id.lower() for part in allow_from.split(",")
    )


def csv_contains(csv: str, value: str) -> bool:
    """Check whether value is present in a comma-separated id list.

    Unlike allow_list, an empty list means "matches nothing" (the opposite
    default), since this is used for opt-in overrides like
    group_reply_all_guilds rather than access control. "*" matches
    everything. Comparison is case-insensitive.
    """
    csv = csv.strip()
    if csv == "":
        return False
    if csv == "*":
        return True
    return any(part.strip().lower() == value.lower() for part in csv.split(","))
