"""Owner-scoped in-memory reply-tree indexes for serial QWEN context."""

from __future__ import annotations

from collections.abc import Mapping

from agentic_perp_trading_bot.schemas import (
    OwnerId,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TelegramPromptMessage,
)


class InMemoryReplyTreeIndex:
    """Maintain one Telegram reply tree for one owner-specific QWEN agent."""

    def __init__(self) -> None:
        self._messages: dict[tuple[str, str], TelegramMessageEnvelope] = {}
        self._children: dict[tuple[str, str], set[str]] = {}

    def add(self, message: TelegramMessageEnvelope) -> None:
        key = (message.channel_id, message.telegram_message_id)
        previous = self._messages.get(key)
        if previous is not None and previous.reply_to_message_id is not None:
            self._children[
                (message.channel_id, previous.reply_to_message_id)
            ].discard(message.telegram_message_id)

        self._messages[key] = message
        if message.reply_to_message_id is not None:
            self._children.setdefault(
                (message.channel_id, message.reply_to_message_id), set()
            ).add(message.telegram_message_id)

    def parent_messages_for(self, message: TelegramMessageEnvelope) -> list[str]:
        """Return all earlier nodes in the reply tree, oldest first."""
        direct_parent_id = message.reply_to_message_id
        if direct_parent_id is None:
            return []

        root_id = self._find_root(message.channel_id, direct_parent_id)
        current_id = int(message.telegram_message_id)
        traversed: set[str] = set()
        visited: set[str] = set()

        def traverse(message_id: str) -> None:
            if message_id in visited:
                return
            visited.add(message_id)
            if int(message_id) < current_id:
                traversed.add(message_id)
            for child_id in sorted(
                self._children.get((message.channel_id, message_id), set()),
                key=int,
            ):
                if int(child_id) < current_id:
                    traverse(child_id)

        traverse(root_id)
        return sorted(traversed, key=int)

    def prompt_context_for(self, message: TelegramMessageEnvelope) -> TelegramPromptContext:
        parent_messages = []
        for message_id in self.parent_messages_for(message):
            parent = self._messages.get((message.channel_id, message_id))
            parent_messages.append(
                TelegramPromptMessage.from_envelope(parent)
                if parent is not None
                else TelegramPromptMessage(telegram_message_id=message_id)
            )
        return TelegramPromptContext.from_message(message, parent_messages)

    def _find_root(self, channel_id: str, message_id: str) -> str:
        root_id = message_id
        visited: set[str] = set()
        while root_id not in visited:
            visited.add(root_id)
            parent = self._messages.get((channel_id, root_id))
            if parent is None or parent.reply_to_message_id is None:
                return root_id
            root_id = parent.reply_to_message_id
        return root_id


class InMemoryReplyTreeIndexRegistry:
    """Keep separate reply trees for the four owner-specific QWEN agents."""

    def __init__(
        self,
        indexes: Mapping[OwnerId, InMemoryReplyTreeIndex] | None = None,
    ) -> None:
        self._indexes = {owner_id: InMemoryReplyTreeIndex() for owner_id in OwnerId}
        if indexes is not None:
            self._indexes.update(indexes)

    def for_owner(self, owner_id: OwnerId) -> InMemoryReplyTreeIndex:
        return self._indexes[owner_id]
