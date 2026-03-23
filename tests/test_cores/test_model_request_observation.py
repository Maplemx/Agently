import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from agently import Agently
from agently.core import ModelRequest, PluginManager
from agently.types.data import AgentlyRequestData, RunContext
from agently.utils import Settings


class MockObservationRequester:
    name = "MockObservationRequester"
    DEFAULT_SETTINGS: dict[str, Any] = {}
    attempts = 0

    def __init__(self, prompt, settings):
        self.prompt = prompt
        self.settings = settings

    @classmethod
    def reset(cls):
        cls.attempts = 0

    @staticmethod
    def _on_register():
        pass

    @staticmethod
    def _on_unregister():
        pass

    def generate_request_data(self):
        type(self).attempts += 1
        prompt_object = self.prompt.to_prompt_object()
        return AgentlyRequestData(
            client_options={},
            headers={},
            data={
                "attempt": type(self).attempts,
                "messages": self.prompt.to_messages(),
                "prompt_text": self.prompt.to_text(),
                "output_format": prompt_object.output_format,
            },
            request_options={"stream": True},
            request_url="mock://observation-requester",
        )

    async def request_model(self, request_data: AgentlyRequestData):
        attempt = int(request_data.data.get("attempt", 1))
        output_format = str(request_data.data.get("output_format", "markdown"))
        if output_format == "json":
            if attempt == 1:
                yield "message", json.dumps({"summary": "retry me"}, ensure_ascii=False)
            else:
                yield "message", json.dumps({"summary": "all good", "reply": "done"}, ensure_ascii=False)
            return
        yield "message", "Morning briefing prepared.\nHighlight GPU demand.\n"

    async def broadcast_response(
        self,
        response_generator: AsyncGenerator[tuple[str, Any], None],
    ):
        response_text = ""
        async for event, data in response_generator:
            if event == "message":
                response_text += str(data)
        for line in response_text.splitlines(keepends=True):
            if line:
                yield "delta", line
                await asyncio.sleep(0)
        yield "done", response_text
        yield "meta", {"provider": "mock-observation", "model": "mock-1"}


def _create_request():
    settings = Settings(name="ObservationTestSettings", parent=Agently.settings)
    plugin_manager = PluginManager(settings, parent=Agently.plugin_manager, name="ObservationTestPluginManager")
    plugin_manager.register("ModelRequester", MockObservationRequester, activate=True)
    return ModelRequest(
        plugin_manager,
        agent_name="observation-agent",
        agent_id="agent-observation",
        parent_settings=settings,
    )


@pytest.mark.asyncio
async def test_model_request_events_include_prompt_and_child_run_lineage():
    MockObservationRequester.reset()
    captured = []

    async def capture(event):
        captured.append(event)

    hook_name = "test_model_request_observation.capture"
    Agently.event_center.register_hook(capture, hook_name=hook_name)
    try:
        workflow_run = RunContext.create(
            run_kind="workflow_execution",
            agent_name="workflow-agent",
            execution_id="execution-observation",
            meta={"flow_name": "observation-flow"},
        )
        request = _create_request()
        request.input("Summarize the morning operations notes.")
        request.instruct("Focus on GPU cloud demand and operational risk.")

        response = request.get_response(parent_run_context=workflow_run)
        text = await response.async_get_text()

        assert "Morning briefing prepared." in text
        assert response.run_context.parent_run_id == workflow_run.run_id
        assert response.model_run_context.parent_run_id == response.run_context.run_id
        assert response.model_run_context.run_kind == "model_request"

        request_events = [event for event in captured if event.run and event.run.run_id == response.run_context.run_id]
        model_events = [event for event in captured if event.run and event.run.run_id == response.model_run_context.run_id]

        assert [event.event_type for event in request_events if event.event_type.startswith("request.")] == [
            "request.started",
            "request.completed",
        ]
        assert [event.event_type for event in model_events] == [
            "model.request_started",
            "prompt.built",
            "model.requesting",
            "model.streaming",
            "model.streaming",
            "model.completed",
            "model.meta",
        ]

        prompt_event = next(event for event in model_events if event.event_type == "prompt.built")
        assert "Summarize the morning operations notes." in str(prompt_event.payload["prompt"]["input"])
        assert "GPU cloud demand" in str(prompt_event.payload["prompt_text"])

        requesting_event = next(event for event in model_events if event.event_type == "model.requesting")
        assert requesting_event.payload["request"]["request_url"] == "mock://observation-requester"
        assert requesting_event.payload["attempt_index"] == 1

        meta_event = next(event for event in model_events if event.event_type == "model.meta")
        assert meta_event.payload["meta"]["provider"] == "mock-observation"
        assert meta_event.payload["meta"]["model"] == "mock-1"
    finally:
        Agently.event_center.unregister_hook(hook_name)


@pytest.mark.asyncio
async def test_model_request_retry_creates_multiple_attempt_runs():
    MockObservationRequester.reset()
    captured = []

    async def capture(event):
        captured.append(event)

    hook_name = "test_model_request_observation.retry_capture"
    Agently.event_center.register_hook(capture, hook_name=hook_name)
    try:
        request = _create_request()
        request.input("Return a structured operations update.")
        request.output(
            {
                "summary": (str,),
                "reply": (str,),
            }
        )

        response = request.get_response()
        data = await response.async_get_data(ensure_keys=["reply"], max_retries=1)

        assert data["reply"] == "done"

        attempt_start_events = [event for event in captured if event.event_type == "model.request_started"]
        assert len(attempt_start_events) == 2
        assert [event.payload["attempt_index"] for event in attempt_start_events] == [1, 2]
        assert len({event.run.run_id for event in attempt_start_events if event.run is not None}) == 2
        assert all(event.run and event.run.parent_run_id == response.run_context.run_id for event in attempt_start_events)

        retry_event = next(event for event in captured if event.event_type == "model.retrying")
        assert retry_event.payload["next_attempt_index"] == 2
        assert retry_event.run is not None
        assert retry_event.run.run_id == response.run_context.run_id
    finally:
        Agently.event_center.unregister_hook(hook_name)
