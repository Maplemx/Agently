from typing import Any, Literal, Awaitable, Callable, TypeAlias, TYPE_CHECKING
from typing_extensions import TypedDict, NotRequired

if TYPE_CHECKING:
    from agently.utils import Settings
    from agently.types.data import SerializableData, ChatMessage

MemoResizeType: TypeAlias = Literal["lite", "deep"] | str


class MemoResizeDecision(TypedDict):
    type: MemoResizeType
    reason: NotRequired[str]
    severity: NotRequired[int]
    meta: NotRequired[dict[str, Any]]


MemoResizePolicyResult: TypeAlias = "MemoResizeType | MemoResizeDecision | None"

MemoResizePolicyHandler: TypeAlias = (
    "Callable[[list[ChatMessage], list[ChatMessage], Settings], MemoResizePolicyResult | Awaitable[MemoResizePolicyResult]]"
)

MemoResizePolicyAsyncHandler: TypeAlias = (
    "Callable[[list[ChatMessage], list[ChatMessage], Settings], Awaitable[MemoResizePolicyResult]]"
)

MemoResizeHandlerResult: TypeAlias = "tuple[list[ChatMessage], list[ChatMessage], SerializableData]"

MemoResizeHandler: TypeAlias = (
    "Callable[[list[ChatMessage], list[ChatMessage], SerializableData, Settings], MemoResizeHandlerResult | Awaitable[MemoResizeHandlerResult]]"
)

MemoResizeAsyncHandler: TypeAlias = (
    "Callable[[list[ChatMessage], list[ChatMessage], SerializableData, Settings], Awaitable[MemoResizeHandlerResult]]"
)

AttachmentSummary: TypeAlias = "dict[str, Any]"
AttachmentSummaryHandler: TypeAlias = (
    "Callable[[ChatMessage], list[AttachmentSummary] | Awaitable[list[AttachmentSummary]]]"
)

AttachmentSummaryAsyncHandler: TypeAlias = "Callable[[ChatMessage], Awaitable[list[AttachmentSummary]]]"
