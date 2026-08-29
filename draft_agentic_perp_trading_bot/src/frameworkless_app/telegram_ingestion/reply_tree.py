"""Owner-scoped reply trees for serial QWEN context and ElastiCache storage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

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


class ReplyTreeStore(Protocol):
    async def add(self, message: TelegramMessageEnvelope) -> None: ...

    async def parent_messages_for(
        self,
        message: TelegramMessageEnvelope,
    ) -> list[str]: ...

    async def prompt_context_for(
        self,
        message: TelegramMessageEnvelope,
    ) -> TelegramPromptContext: ...


class InMemoryReplyTreeStore:
    """Process-local test adapter matching the shared ElastiCache contract."""

    def __init__(
        self,
        registry: InMemoryReplyTreeIndexRegistry | None = None,
    ) -> None:
        self.registry = registry or InMemoryReplyTreeIndexRegistry()

    async def add(self, message: TelegramMessageEnvelope) -> None:
        self.registry.for_owner(message.owner_id).add(message)

    async def parent_messages_for(
        self,
        message: TelegramMessageEnvelope,
    ) -> list[str]:
        return self.registry.for_owner(message.owner_id).parent_messages_for(message)

    async def prompt_context_for(
        self,
        message: TelegramMessageEnvelope,
    ) -> TelegramPromptContext:
        return self.registry.for_owner(message.owner_id).prompt_context_for(message)


class ElastiCacheClient(Protocol):
    """Minimal asynchronous Redis-compatible operations required by this store."""

    async def get(self, key: str) -> str | bytes | None: ...

    async def set(self, key: str, value: str) -> object: ...

    async def sadd(self, key: str, *values: str) -> object: ...

    async def srem(self, key: str, *values: str) -> object: ...

    async def smembers(self, key: str) -> set[str] | set[bytes]: ...


class ElastiCacheReplyTreeStore:
    """Redis-compatible owner reply trees shared across Lightsail workers."""

    def __init__(
        self,
        client: ElastiCacheClient,
        *,
        key_prefix: str = "agentic-perp:reply-tree",
    ) -> None:
        self._client = client
        self._key_prefix = key_prefix.rstrip(":")
        self._local_messages: dict[
            tuple[OwnerId, str, str],
            TelegramMessageEnvelope,
        ] = {}

    async def add(self, message: TelegramMessageEnvelope) -> None:
        previous = await self._get_message(
            message.owner_id,
            message.channel_id,
            message.telegram_message_id,
        )
        if previous is not None and previous.reply_to_message_id is not None:
            await self._client.srem(
                self._children_key(
                    message.owner_id,
                    message.channel_id,
                    previous.reply_to_message_id,
                ),
                message.telegram_message_id,
            )

        await self._client.set(
            self._message_key(
                message.owner_id,
                message.channel_id,
                message.telegram_message_id,
            ),
            message.model_dump_json(),
        )
        self._local_messages[
            (message.owner_id, message.channel_id, message.telegram_message_id)
        ] = message
        if message.reply_to_message_id is not None:
            await self._client.sadd(
                self._children_key(
                    message.owner_id,
                    message.channel_id,
                    message.reply_to_message_id,
                ),
                message.telegram_message_id,
            )

    async def parent_messages_for(
        self,
        message: TelegramMessageEnvelope,
    ) -> list[str]:
        direct_parent_id = message.reply_to_message_id
        if direct_parent_id is None:
            return []

        loaded: dict[str, TelegramMessageEnvelope | None] = {}

        async def load(message_id: str) -> TelegramMessageEnvelope | None:
            if message_id not in loaded:
                loaded[message_id] = await self._get_message(
                    message.owner_id,
                    message.channel_id,
                    message_id,
                )
            return loaded[message_id]

        root_id = direct_parent_id
        visited_roots: set[str] = set()
        while root_id not in visited_roots:
            visited_roots.add(root_id)
            parent = await load(root_id)
            if parent is None or parent.reply_to_message_id is None:
                break
            root_id = parent.reply_to_message_id

        current_id = int(message.telegram_message_id)
        traversed: set[str] = set()
        visited: set[str] = set()

        async def traverse(message_id: str) -> None:
            if message_id in visited:
                return
            visited.add(message_id)
            if int(message_id) < current_id:
                traversed.add(message_id)
            child_ids = await self._client.smembers(
                self._children_key(
                    message.owner_id,
                    message.channel_id,
                    message_id,
                )
            )
            normalized_children = sorted(
                (_decode_cache_value(child_id) for child_id in child_ids),
                key=int,
            )
            for child_id in normalized_children:
                if int(child_id) < current_id:
                    await traverse(child_id)

        await traverse(root_id)
        return sorted(traversed, key=int)

    async def prompt_context_for(
        self,
        message: TelegramMessageEnvelope,
    ) -> TelegramPromptContext:
        prompt_parents = []
        for message_id in await self.parent_messages_for(message):
            parent = await self._get_message(
                message.owner_id,
                message.channel_id,
                message_id,
            )
            prompt_parents.append(
                TelegramPromptMessage.from_envelope(parent)
                if parent is not None
                else TelegramPromptMessage(telegram_message_id=message_id)
            )
        return TelegramPromptContext.from_message(message, prompt_parents)

    async def _get_message(
        self,
        owner_id: OwnerId,
        channel_id: str,
        message_id: str,
    ) -> TelegramMessageEnvelope | None:
        local_key = (owner_id, channel_id, message_id)
        if local_key in self._local_messages:
            return self._local_messages[local_key]
        value = await self._client.get(
            self._message_key(owner_id, channel_id, message_id)
        )
        if value is None:
            return None
        message = TelegramMessageEnvelope.model_validate_json(
            _decode_cache_value(value)
        )
        self._local_messages[local_key] = message
        return message

    def _message_key(
        self,
        owner_id: OwnerId,
        channel_id: str,
        message_id: str,
    ) -> str:
        return f"{self._key_prefix}:{owner_id}:{channel_id}:message:{message_id}"

    def _children_key(
        self,
        owner_id: OwnerId,
        channel_id: str,
        message_id: str,
    ) -> str:
        return f"{self._key_prefix}:{owner_id}:{channel_id}:children:{message_id}"


def _decode_cache_value(value: str | bytes) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else value
