# Copyright 2023-2025 AgentEra(Agently.Tech)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from typing import TYPE_CHECKING

from agently.types.plugins import EventHooker

COLORS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "gray": 90,
}


def color_text(text: str, color: str | None = None, bold: bool = False, underline: bool = False) -> str:
    codes = []
    if bold:
        codes.append("1")
    if underline:
        codes.append("4")
    if color and color in COLORS:
        codes.append(str(COLORS[color]))
    if not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


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

        settings = message.content["settings"]

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
                    if settings["runtime.show_model_logs"]:
                        if (
                            SystemMessageHooker._current_meta["table_name"] == message_data["agent_name"]
                            and SystemMessageHooker._current_meta["row_id"] == message_data["response_id"]
                            and SystemMessageHooker._current_meta["stage"] == content["stage"]
                        ):
                            print(color_text(content["detail"], color="gray"), end="", flush=True)
                        else:
                            header = color_text(
                                f"[Agent-{ message_data['agent_name'] }] - [Request-{ message_data['response_id'] }]",
                                color="blue",
                                bold=True,
                            )
                            stage_label = color_text("Stage:", color="cyan", bold=True)
                            stage_val = color_text(content["stage"], color="yellow", underline=True)
                            detail_label = color_text("Detail:\n", color="cyan", bold=True)
                            detail = color_text(content["detail"], color="green")
                            print(f"{header}\n{stage_label} {stage_val}\n{detail_label}{detail}", end="")
                            SystemMessageHooker._current_meta["table_name"] = message_data["agent_name"]
                            SystemMessageHooker._current_meta["row_id"] = message_data["response_id"]
                            SystemMessageHooker._current_meta["stage"] = content["stage"]
                else:
                    if SystemMessageHooker._streaming is True and settings["runtime.show_model_logs"]:
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
                    if settings["runtime.show_model_logs"]:
                        header = color_text(
                            f"[Agent-{ message_data['agent_name'] }] - [Response-{ message_data['response_id'] }]",
                            color="blue",
                            bold=True,
                        )
                        stage_label = color_text("Stage:", color="cyan", bold=True)
                        stage_val = color_text(content["stage"], color="yellow", underline=True)
                        detail_label = color_text("Detail:\n", color="cyan", bold=True)
                        detail = color_text(f"{content['detail']}", color="gray")
                        await event_center.async_emit(
                            "log",
                            {
                                "level": "INFO",
                                "content": f"{header}\n{stage_label} {stage_val}\n{detail_label}{detail}",
                            },
                        )
            case "TOOL":
                if settings["runtime.show_tool_logs"]:
                    tool_title = color_text("[Tool Using Result]:", color="blue", bold=True)
                    tool_body = color_text(str(message.content["data"]), color="gray")
                    await event_center.async_emit(
                        "log",
                        {
                            "level": "INFO",
                            "content": f"{tool_title}\n{tool_body}",
                        },
                    )
            case "TRIGGER_FLOW":
                if settings["runtime.show_trigger_flow_logs"]:
                    trigger = color_text(f"[TriggerFlow] { message.content['data'] }", color="yellow", bold=True)
                    await event_center.async_emit(
                        "log",
                        {
                            "level": "INFO",
                            "content": trigger,
                        },
                    )
