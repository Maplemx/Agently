from __future__ import annotations

from typing import Any, Literal, TYPE_CHECKING, cast
import inspect
import json
import uuid
import yaml

from agently.utils import Settings, DataFormatter, DataLocator, FunctionShifter
from agently.core import ModelRequest
from agently.core import ModelRequest
from agently.types.data import ChatMessage

if TYPE_CHECKING:
    from agently.base import Agent
    from agently.types.data import SerializableData, ChatMessageDict
    from agently.types.plugins import (
        MemoResizePolicyHandler,
        MemoResizePolicyAsyncHandler,
        MemoResizeHandler,
        MemoResizeAsyncHandler,
        MemoResizeDecision,
        MemoResizePolicyResult,
        AttachmentSummaryHandler,
        AttachmentSummaryAsyncHandler,
    )


class Session:
    def __init__(
        self,
        *,
        policy_handler: "MemoResizePolicyHandler | None" = None,
        resize_handlers: "dict[Literal['lite', 'deep'] | str, MemoResizeHandler] | None" = None,
        attachment_summary_handler: "AttachmentSummaryHandler | None" = None,
        parent_settings: Settings | None = None,
        agent: "Agent | None" = None,
    ):
        self.id = uuid.uuid4().hex
        self.full_chat_history = []
        self.current_chat_history = []
        self.memo = {}
        self._turns = 0
        self._last_resize_turn = 0
        self._memo_cursor = 0

        self._policy_handler: MemoResizePolicyAsyncHandler = cast(
            "MemoResizePolicyAsyncHandler",
            FunctionShifter.asyncify(policy_handler or self._default_policy_handler),
        )
        if resize_handlers is None:
            resize_handlers = {
                "lite": self._default_lite_resize_handler,
                "deep": self._default_deep_resize_handler,
            }
        self._resize_handlers: dict[Literal["lite", "deep"] | str, MemoResizeAsyncHandler] = {
            key: cast("MemoResizeAsyncHandler", FunctionShifter.asyncify(handler))
            for key, handler in resize_handlers.items()
        }
        self._attachment_summary_handler: AttachmentSummaryAsyncHandler = cast(
            "AttachmentSummaryAsyncHandler",
            FunctionShifter.asyncify(attachment_summary_handler or self._default_attachment_summary_handler),
        )
        self.settings = Settings(parent=parent_settings)
        self._agent = agent

        self.settings.setdefault("session.resize.every_n_turns", 8)
        self.settings.setdefault("session.resize.max_messages_text_length", 12_000)
        self.settings.setdefault("session.resize.max_keep_messages_count", None)
        self.settings.setdefault(
            "session.memo.instruct",
            [
                "Update the memo dictionary based on the provided messages.",
                "Keep stable preferences, constraints, and facts that help future turns.",
                "Add new keys or update existing ones as needed.",
                "Return the updated memo dictionary.",
            ],
        )

        self.set_settings = self.settings.set_settings
        self.judge_resize = FunctionShifter.syncify(self.async_judge_resize)
        self.resize = FunctionShifter.syncify(self.async_resize)

    def _approx_message_chars(self, message: "ChatMessage") -> int:
        content = message.content
        if isinstance(content, str):
            return len(content)
        if isinstance(content, list):
            total = 0
            for part in content:
                if isinstance(part, str):
                    total += len(part)
                elif isinstance(part, dict):
                    if "text" in part and isinstance(part["text"], str):
                        total += len(part["text"])
                    else:
                        total += len(json.dumps(part, ensure_ascii=False, default=str))
                else:
                    total += len(str(part))
            return total
        return len(str(content))

    def _approx_chat_history_chars(self, chat_history: "list[ChatMessage]") -> int:
        return sum(len(m.role) + 1 + self._approx_message_chars(m) for m in chat_history)

    def _get_setting(self, key: str, legacy_key: str | None, default: Any) -> Any:
        sentinel = object()
        value = self.settings.get(key, sentinel)
        if value is not sentinel:
            return value
        if legacy_key is None:
            return default
        legacy_value = self.settings.get(legacy_key, sentinel)
        if legacy_value is not sentinel:
            return legacy_value
        return default

    def _get_model_requester(self):
        if self._agent:
            return ModelRequest(
                self._agent.plugin_manager,
                agent_name=self._agent.name,
                parent_settings=self.settings,
            )
        from agently.base import plugin_manager

        return ModelRequest(
            plugin_manager,
            parent_settings=self.settings,
        )

    def _serialize_chat_history(self, chat_history: "list[ChatMessage]") -> list[dict[str, Any]]:
        return [DataFormatter.sanitize(message.model_dump()) for message in chat_history]

    def _dump_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "memo": DataFormatter.sanitize(self.memo),
            "full_chat_history": self._serialize_chat_history(self.full_chat_history),
            "current_chat_history": self._serialize_chat_history(self.current_chat_history),
            "settings": DataFormatter.sanitize(self.settings.get()),
            "turns": self._turns,
            "last_resize_turn": self._last_resize_turn,
            "memo_cursor": self._memo_cursor,
        }

    def to_json(self) -> str:
        return json.dumps(self._dump_data(), ensure_ascii=True)

    def to_yaml(self) -> str:
        return yaml.safe_dump(self._dump_data(), allow_unicode=False)

    def _load_data(self, data: dict[str, Any]):
        from agently.types.data.prompt import validate_chat_history

        if not isinstance(data, dict):
            raise TypeError("Session.load expects a dictionary data object.")
        if "id" in data:
            self.id = str(data["id"])
        if "memo" in data:
            self.memo = data["memo"]
        if "full_chat_history" in data:
            self.full_chat_history = validate_chat_history(data["full_chat_history"])
        if "current_chat_history" in data:
            self.current_chat_history = validate_chat_history(data["current_chat_history"])
        if "settings" in data and isinstance(data["settings"], dict):
            self.settings.update(data["settings"])
        if "turns" in data:
            self._turns = int(data["turns"])
        if "last_resize_turn" in data:
            self._last_resize_turn = int(data["last_resize_turn"])
        if "memo_cursor" in data:
            self._memo_cursor = int(data["memo_cursor"])
        return self

    def _ensure_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]

    def _get_memo_instruct(self) -> list[str]:
        base = self._ensure_list(self.settings.get("session.memo.instruct", []))
        return [str(item) for item in base if item is not None]

    async def _update_memo_with_model(
        self,
        memo: dict[str, Any],
        messages: "list[ChatMessage]",
    ) -> dict[str, Any]:
        if not messages:
            return memo
        requester = self._get_model_requester()
        attachments = await self._collect_attachment_refs(messages)
        prompt_input = {
            "current_memo": memo,
            "messages": self._serialize_chat_history(messages),
            "attachments": attachments,
        }
        output_schema = {"memo": (dict[str, Any], "Updated memo dictionary")}
        result = requester.input(prompt_input).instruct(self._get_memo_instruct()).output(output_schema)
        data = await result.async_get_data()
        if isinstance(data, dict) and isinstance(data.get("memo"), dict):
            return data["memo"]
        if isinstance(data, dict):
            return data
        return memo

    def _chunk_by_max_chars(
        self,
        chat_history: "list[ChatMessage]",
        max_chars: int,
    ) -> list["list[ChatMessage]"]:
        if max_chars <= 0:
            return [chat_history] if chat_history else []
        chunks: list[list[ChatMessage]] = []
        current: list[ChatMessage] = []
        current_chars = 0
        for message in chat_history:
            message_chars = len(message.role) + 1 + self._approx_message_chars(message)
            if current and current_chars + message_chars > max_chars:
                chunks.append(current)
                current = [message]
                current_chars = message_chars
            else:
                current.append(message)
                current_chars += message_chars
        if current:
            chunks.append(current)
        return chunks

    def load_json(self, value: str):
        self._load_data(json.loads(value))
        return self

    def load_yaml(self, value: str):
        self._load_data(yaml.safe_load(value))
        return self

    def _split_by_max_chars(
        self,
        chat_history: "list[ChatMessage]",
        max_chars: int,
    ) -> tuple["list[ChatMessage]", "list[ChatMessage]"]:
        if max_chars <= 0 or not chat_history:
            return [], chat_history

        kept: list[ChatMessage] = []
        kept_chars = 0
        for message in reversed(chat_history):
            message_chars = len(message.role) + 1 + self._approx_message_chars(message)
            if kept and kept_chars + message_chars > max_chars:
                break
            kept.append(message)
            kept_chars += message_chars

        kept.reverse()
        pruned = chat_history[: len(chat_history) - len(kept)]
        return pruned, kept

    def _default_attachment_summary_handler(self, message: "ChatMessage") -> list[dict[str, Any]]:
        content = message.content
        if not isinstance(content, list):
            return []
        summaries: list[dict[str, Any]] = []
        for part in content:
            if isinstance(part, dict):
                payload = part
            elif hasattr(part, "model_dump"):
                payload = part.model_dump()
            else:
                continue
            payload = DataFormatter.sanitize(payload)
            part_type = payload.get("type")
            if not part_type or part_type == "text":
                continue
            ref = None
            for key in ("file", "url", "path", "id", "name"):
                value = DataLocator.locate_path_in_dict(payload, key, default=None)
                if value:
                    ref = value
                    break
            summaries.append(
                {
                    "type": part_type,
                    "ref": ref,
                    "meta": DataFormatter.sanitize(
                        {
                            key: payload.get(key)
                            for key in ("name", "mime_type", "size", "width", "height", "duration")
                            if key in payload
                        }
                    ),
                }
            )
        return summaries

    async def _collect_attachment_refs(self, messages: "list[ChatMessage]") -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for message in messages:
            result = await self._attachment_summary_handler(message)
            if inspect.isawaitable(result):
                result = await result
            refs.extend(cast(list[dict[str, Any]], result))
        return refs

    def _ensure_decision(self, result: "MemoResizePolicyResult") -> "MemoResizeDecision | None":
        if result is None:
            return None
        if isinstance(result, str):
            return {"type": result}
        if isinstance(result, dict) and "type" in result:
            return result
        raise TypeError(f"Invalid policy result: {type(result)} {result}")

    async def _default_policy_handler(
        self,
        full_chat_history: "list[ChatMessage]",
        current_chat_history: "list[ChatMessage]",
        settings: Settings,
    ):
        max_current_chars = self._get_setting(
            "session.resize.max_messages_text_length",
            "session.resize.max_current_chars",
            12_000,
        )
        max_keep_messages_count = self._get_setting(
            "session.resize.max_keep_messages_count",
            "session.resize.keep_last_messages",
            None,
        )
        every_n_turns = settings.get("session.resize.every_n_turns", 8)

        try:
            max_current_chars_int = int(max_current_chars)  # type: ignore
        except Exception:
            max_current_chars_int = 12_000
        try:
            every_n_turns_int = int(every_n_turns)  # type: ignore
        except Exception:
            every_n_turns_int = 8

        if max_current_chars_int > 0 and self._approx_chat_history_chars(current_chat_history) >= max_current_chars_int:
            return {"type": "deep", "reason": "max_messages_text_length", "severity": 100}

        try:
            max_keep_messages_count_int = int(max_keep_messages_count)  # type: ignore[arg-type]
        except Exception:
            max_keep_messages_count_int = None
        if max_keep_messages_count_int and len(current_chat_history) > max_keep_messages_count_int:
            return {"type": "lite", "reason": "max_keep_messages_count", "severity": 50}

        turns_since_last_resize = self._turns - self._last_resize_turn
        if every_n_turns_int > 0 and turns_since_last_resize >= every_n_turns_int:
            return {"type": "lite", "reason": "every_n_turns", "severity": 10}

        return None

    async def _default_lite_resize_handler(
        self,
        full_chat_history: "list[ChatMessage]",
        current_chat_history: "list[ChatMessage]",
        memo: "SerializableData",
        settings: Settings,
    ):
        memo_dict: dict[str, Any] = memo if isinstance(memo, dict) else {}
        delta_messages = full_chat_history[self._memo_cursor :]
        if delta_messages:
            memo_dict = await self._update_memo_with_model(memo_dict, delta_messages)
        self._memo_cursor = len(full_chat_history)

        keep_last_messages = self._get_setting(
            "session.resize.max_keep_messages_count",
            "session.resize.keep_last_messages",
            None,
        )
        max_current_chars = self._get_setting(
            "session.resize.max_messages_text_length",
            "session.resize.max_current_chars",
            12_000,
        )
        try:
            keep_last_messages_int = max(0, int(keep_last_messages))  # type: ignore[arg-type]
        except Exception:
            keep_last_messages_int = None
        try:
            max_current_chars_int = int(max_current_chars)  # type: ignore[arg-type]
        except Exception:
            max_current_chars_int = 12_000

        if keep_last_messages_int is None:
            pruned, remaining = self._split_by_max_chars(current_chat_history, max_current_chars_int)
        else:
            if keep_last_messages_int == 0 or len(current_chat_history) <= keep_last_messages_int:
                return full_chat_history, current_chat_history, memo
            pruned = current_chat_history[:-keep_last_messages_int]
            remaining = current_chat_history[-keep_last_messages_int:]
            if max_current_chars_int > 0:
                extra_pruned, remaining = self._split_by_max_chars(remaining, max_current_chars_int)
                if extra_pruned:
                    pruned = pruned + extra_pruned

        memo_dict["last_resize"] = {"type": "lite", "turn": self._turns, "reason": "lite_resize"}

        return full_chat_history, remaining, memo_dict

    async def _default_deep_resize_handler(
        self,
        full_chat_history: "list[ChatMessage]",
        current_chat_history: "list[ChatMessage]",
        memo: "SerializableData",
        settings: Settings,
    ):
        memo_dict: dict[str, Any] = memo if isinstance(memo, dict) else {}
        max_current_chars = self._get_setting(
            "session.resize.max_messages_text_length",
            "session.resize.max_current_chars",
            12_000,
        )
        try:
            max_current_chars_int = int(max_current_chars)  # type: ignore[arg-type]
        except Exception:
            max_current_chars_int = 12_000
        for batch in self._chunk_by_max_chars(full_chat_history, max_current_chars_int):
            memo_dict = await self._update_memo_with_model(memo_dict, batch)
        self._memo_cursor = len(full_chat_history)

        keep_last_messages = self._get_setting(
            "session.resize.max_keep_messages_count",
            "session.resize.keep_last_messages",
            None,
        )
        try:
            keep_last_messages_int = max(0, int(keep_last_messages))  # type: ignore[arg-type]
        except Exception:
            keep_last_messages_int = None

        if keep_last_messages_int is None:
            pruned, remaining = self._split_by_max_chars(current_chat_history, max_current_chars_int)
        else:
            if keep_last_messages_int == 0:
                pruned = current_chat_history
                remaining = []
            elif len(current_chat_history) <= keep_last_messages_int:
                pruned = []
                remaining = current_chat_history
            else:
                pruned = current_chat_history[:-keep_last_messages_int]
                remaining = current_chat_history[-keep_last_messages_int:]
            if max_current_chars_int > 0 and remaining:
                extra_pruned, remaining = self._split_by_max_chars(remaining, max_current_chars_int)
                if extra_pruned:
                    pruned = pruned + extra_pruned

        memo_dict["last_resize"] = {"type": "deep", "turn": self._turns, "reason": "deep_resize"}

        return full_chat_history, remaining, memo_dict

    def set_policy_handler(self, policy_handler: "MemoResizePolicyHandler"):
        self._policy_handler = cast("MemoResizePolicyAsyncHandler", FunctionShifter.asyncify(policy_handler))
        return self

    def set_attachment_summary_handler(self, attachment_summary_handler: "AttachmentSummaryHandler"):
        self._attachment_summary_handler = cast(
            "AttachmentSummaryAsyncHandler",
            FunctionShifter.asyncify(attachment_summary_handler),
        )
        return self

    def set_resize_handlers(self, resize_type: Literal["lite", "deep"] | str, resize_handler: "MemoResizeHandler"):
        self._resize_handlers[resize_type] = cast(
            "MemoResizeAsyncHandler",
            FunctionShifter.asyncify(resize_handler),
        )
        return self

    def append_message(self, message: "ChatMessage | ChatMessageDict"):
        if isinstance(message, dict):
            message = ChatMessage(
                role=message["role"],
                content=message["content"],
            )
        self.full_chat_history.append(message)
        self.current_chat_history.append(message)
        if message.role == "assistant":
            self._turns += 1
        return self

    async def async_judge_resize(self, force: Literal["lite", "deep", False, None] | str = False):
        if force:
            decision: "MemoResizeDecision | None" = {
                "type": str(force) if isinstance(force, str) else "deep",
                "reason": "force",
                "severity": 1000,
            }
        else:
            policy_result = await self._policy_handler(
                self.full_chat_history,
                self.current_chat_history,
                self.settings,
            )
            if inspect.isawaitable(policy_result):
                policy_result = await policy_result
            decision = self._ensure_decision(cast("MemoResizePolicyResult", policy_result))

        if decision is None:
            return None

        return decision

    async def async_resize(self, force: Literal["lite", "deep", False, None] | str = False):
        decision = await self.async_judge_resize(force=force)
        if decision is None:
            return self.current_chat_history

        resize_type = decision["type"]
        handler = self._resize_handlers.get(resize_type)
        if handler is None:
            raise KeyError(f"Missing resize handler for type: {resize_type}")

        handler_result = await handler(
            self.full_chat_history,
            self.current_chat_history,
            self.memo,
            self.settings,
        )
        if inspect.isawaitable(handler_result):
            handler_result = await handler_result
        self.full_chat_history, self.current_chat_history, self.memo = handler_result
        if isinstance(self.memo, dict) and isinstance(decision, dict) and decision.get("reason"):
            last_resize = self.memo.get("last_resize")
            if not isinstance(last_resize, dict):
                last_resize = {}
                self.memo["last_resize"] = last_resize
            last_resize["reason"] = decision["reason"] if "reason" in decision else ""
        self._last_resize_turn = self._turns
        return self.current_chat_history
