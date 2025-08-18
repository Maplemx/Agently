from typing import TYPE_CHECKING

from agently.types.plugins import EventHooker

if TYPE_CHECKING:
    from agently.types.data import EventMessage, AgentlySystemEvent


class SystemMessageHooker(EventHooker):
    name = "SystemMessageHooker"
    events = ["AGENTLY_SYS"]

    _current_meta = {
        "table_name": None,
        "row_id": None,
        "stage": None,
    }
    _streaming = False

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    @staticmethod
    async def handler(message: "EventMessage"):
        from agently.base import event_center

        message_type: "AgentlySystemEvent" = message.content["type"]
        match message_type:
            case "MODEL_REQUEST":
                message_data = message.content["data"]
                content = message_data["content"]
                if "delta" in content and content["delta"] is True:
                    SystemMessageHooker._streaming = True
                    await event_center.async_emit(
                        "console",
                        {
                            "content": {
                                "Stage": content["stage"],
                                f"${ content['stage'] }": content["detail"],
                            },
                            "meta": {
                                "table_name": f"Agent-{ message_data['agent_name'] }",
                                "row_id": f"Request-{ message_data['response_id'] }",
                            },
                        },
                    )
                    if (
                        SystemMessageHooker._current_meta["table_name"] == message_data["agent_name"]
                        and SystemMessageHooker._current_meta["row_id"] == message_data["response_id"]
                        and SystemMessageHooker._current_meta["stage"] == content["stage"]
                    ):
                        print(content["detail"], end="")
                    else:
                        print(
                            f"[Agent-{ message_data['agent_name'] }] - [Request-{ message_data['response_id'] }]\nStage: { content['stage'] }\nDetail:\n{ content['detail'] }",
                            end="",
                        )
                        SystemMessageHooker._current_meta["table_name"] = message_data["agent_name"]
                        SystemMessageHooker._current_meta["row_id"] = message_data["response_id"]
                        SystemMessageHooker._current_meta["stage"] = content["stage"]
                else:
                    if SystemMessageHooker._streaming is True:
                        print()
                        SystemMessageHooker._streaming = False
                    await event_center.async_emit(
                        "console",
                        {
                            "content": {
                                "Stage": content["stage"],
                                content['stage']: content["detail"],
                            },
                            "meta": {
                                "table_name": f"Agent-{ message_data['agent_name'] }",
                                "row_id": f"Request-{ message_data['response_id'] }",
                            },
                        },
                    )
                    await event_center.async_emit(
                        "log",
                        {
                            "level": "INFO",
                            "content": f"[Agent-{ message_data['agent_name'] }] - [Request-{ message_data['response_id'] }]\nStage: { content['stage'] }\nDetail:\n{ content['detail'] }",
                        },
                    )
