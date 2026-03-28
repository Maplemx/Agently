import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from agently import Agently, TriggerFlow, TriggerFlowRuntimeData
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


def _create_agent():
    settings = Settings(name="ObservationTestAgentSettings", parent=Agently.settings)
    plugin_manager = PluginManager(settings, parent=Agently.plugin_manager, name="ObservationTestAgentPluginManager")
    plugin_manager.register("ModelRequester", MockObservationRequester, activate=True)
    return Agently.AgentType(
        plugin_manager,
        parent_settings=settings,
        name="observation-agent",
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

        completed_events = [event for event in captured if event.event_type == "model.completed"]
        assert len(completed_events) == 2
        final_completed_event = completed_events[-1]
        assert final_completed_event.payload["result"] == {
            "summary": "all good",
            "reply": "done",
        }
        assert final_completed_event.payload["raw_text"] == '{"summary": "all good", "reply": "done"}'
        assert final_completed_event.payload["cleaned_text"] == '{"summary": "all good", "reply": "done"}'
    finally:
        Agently.event_center.unregister_hook(hook_name)


@pytest.mark.asyncio
async def test_agent_turn_wraps_request_and_model_request_runs():
    MockObservationRequester.reset()
    captured = []

    async def capture(event):
        captured.append(event)

    hook_name = "test_model_request_observation.agent_turn_capture"
    Agently.event_center.register_hook(capture, hook_name=hook_name)
    try:
        workflow_run = RunContext.create(
            run_kind="workflow_execution",
            agent_name="workflow-agent",
            execution_id="execution-agent-turn",
            meta={"flow_name": "agent-turn-flow"},
        )
        agent = _create_agent()
        agent.input("Summarize the morning operations notes.")
        agent.instruct("Focus on GPU cloud demand and operational risk.")

        text = await agent.async_get_text(parent_run_context=workflow_run)

        assert "Morning briefing prepared." in text

        turn_events = [event for event in captured if event.run and event.run.run_kind == "agent_turn"]
        assert [event.event_type for event in turn_events] == [
            "agent_turn.started",
            "agent_turn.completed",
        ]

        turn_run = turn_events[0].run
        assert turn_run is not None
        assert turn_run.parent_run_id == workflow_run.run_id

        request_events = [
            event for event in captured if event.run and event.run.run_kind == "request" and event.run.parent_run_id == turn_run.run_id
        ]
        assert [event.event_type for event in request_events if event.event_type.startswith("request.")] == [
            "request.started",
            "request.completed",
        ]

        model_start_event = next(event for event in captured if event.event_type == "model.request_started")
        assert model_start_event.run is not None
        assert model_start_event.run.parent_run_id == request_events[0].run.run_id
    finally:
        Agently.event_center.unregister_hook(hook_name)


@pytest.mark.asyncio
async def test_tool_runtime_uses_action_runs_under_request_scope():
    MockObservationRequester.reset()
    captured = []

    async def capture(event):
        captured.append(event)

    hook_name = "test_model_request_observation.tool_action_capture"
    Agently.event_center.register_hook(capture, hook_name=hook_name)
    try:
        agent = _create_agent()

        agent.tool.register(
            name="lookup_signal",
            desc="lookup external signal",
            kwargs={"topic": (str, "signal topic")},
            func=lambda topic: f"signal:{ topic }",
            tags=[f"agent-{ agent.name }"],
        )

        async def fake_plan_handler(
            _prompt,
            _settings,
            _tool_list,
            _done_plans,
            _last_round_records,
            round_index,
            _max_rounds,
            _agent_name,
        ):
            if round_index == 0:
                return {
                    "next_action": "execute",
                    "execution_commands": [
                        {
                            "purpose": "gather_market_signal",
                            "tool_name": "lookup_signal",
                            "tool_kwargs": {"topic": "gpu"},
                            "todo_suggestion": "respond",
                        }
                    ],
                }
            return {
                "next_action": "response",
                "execution_commands": [],
            }

        async def fake_execution_handler(
            tool_commands,
            _settings,
            _async_call_tool,
            _done_plans,
            _round_index,
            _concurrency,
            _agent_name,
        ):
            return [
                {
                    "purpose": str(tool_commands[0].get("purpose", "unknown")),
                    "tool_name": str(tool_commands[0].get("tool_name", "unknown")),
                    "kwargs": tool_commands[0].get("tool_kwargs", {}),
                    "todo_suggestion": str(tool_commands[0].get("todo_suggestion", "")),
                    "success": True,
                    "result": {"signal": "gpu-demand-rising"},
                    "error": "",
                }
            ]

        agent.register_tool_plan_analysis_handler(fake_plan_handler)
        agent.register_tool_execution_handler(fake_execution_handler)
        agent.tool.tag(["lookup_signal"], f"agent-{ agent.name }")
        agent.input("Need a briefing with external signal.")
        await agent.async_get_text()

        request_run = next(event.run for event in captured if event.event_type == "request.started")
        tool_loop_start = next(event for event in captured if event.event_type == "tool.loop_started")
        assert tool_loop_start.run is not None
        assert request_run is not None
        assert tool_loop_start.run.parent_run_id == request_run.run_id

        action_events = [event for event in captured if event.event_type.startswith("action.")]
        assert [event.event_type for event in action_events] == [
            "action.started",
            "action.completed",
        ]
        action_run = action_events[0].run
        assert action_run is not None
        assert action_run.run_kind == "action"
        assert action_run.parent_run_id == tool_loop_start.run.run_id
        assert action_run.meta.get("action_type") == "tool"
    finally:
        Agently.event_center.unregister_hook(hook_name)


@pytest.mark.asyncio
async def test_trigger_flow_runtime_context_auto_inherits_parent_run_for_agent_and_request():
    MockObservationRequester.reset()
    captured = []

    async def capture(event):
        captured.append(event)

    hook_name = "test_model_request_observation.trigger_flow_runtime_context_capture"
    Agently.event_center.register_hook(capture, hook_name=hook_name)
    try:
        flow = TriggerFlow(name="runtime-context-auto-parent")

        async def run_inside_flow(data: TriggerFlowRuntimeData):
            agent = _create_agent()
            agent.input("Summarize the runtime context flow.")
            request = _create_request()
            request.input("Provide a direct request summary.")
            agent_text = await agent.async_get_text()
            request_text = await request.async_get_text()
            return {
                "agent_text": agent_text,
                "request_text": request_text,
            }

        flow.to(run_inside_flow).end()

        result = await flow.async_start("start")

        assert "Morning briefing prepared." in result["agent_text"]
        assert "Morning briefing prepared." in result["request_text"]

        workflow_start = next(event for event in captured if event.event_type == "workflow.execution_started")
        workflow_run = workflow_start.run
        assert workflow_run is not None

        chunk_start = next(
            event
            for event in captured
            if event.event_type == "chunk.started"
            and event.run is not None
            and event.run.meta.get("chunk_name") == "run_inside_flow"
        )
        chunk_run = chunk_start.run
        assert chunk_run is not None
        assert chunk_run.parent_run_id == workflow_run.run_id

        agent_turn_start = next(event for event in captured if event.event_type == "agent_turn.started")
        assert agent_turn_start.run is not None
        assert agent_turn_start.run.parent_run_id == chunk_run.run_id

        request_starts = [event for event in captured if event.event_type == "request.started"]
        assert len(request_starts) >= 2
        parent_ids = {event.run.parent_run_id for event in request_starts if event.run is not None}
        assert chunk_run.run_id in parent_ids
        assert agent_turn_start.run.run_id in parent_ids
    finally:
        Agently.event_center.unregister_hook(hook_name)


@pytest.mark.asyncio
async def test_nested_subflow_helper_calls_auto_inherit_runtime_context():
    MockObservationRequester.reset()
    captured = []

    async def capture(event):
        captured.append(event)

    hook_name = "test_model_request_observation.nested_subflow_capture"
    Agently.event_center.register_hook(capture, hook_name=hook_name)
    try:
        sub_flow = TriggerFlow(name="daily-news-summary-sub-flow")

        async def summarize_candidate(data: TriggerFlowRuntimeData):
            async def helper():
                agent = _create_agent()
                agent.input("Summarize candidate news.")
                request = _create_request()
                request.input("Summarize direct request in subflow.")
                agent_text = await agent.async_get_text()
                request_text = await request.async_get_text()
                return {
                    "agent_text": agent_text,
                    "request_text": request_text,
                }

            return await helper()

        sub_flow.to(summarize_candidate).end()

        flow = TriggerFlow(name="daily-news-root-flow")
        flow.to_sub_flow(sub_flow, capture={"input": "value"}, write_back={"value": "result"}).end()

        result = await flow.async_start("topic")

        assert "Morning briefing prepared." in result["agent_text"]
        assert "Morning briefing prepared." in result["request_text"]

        workflow_runs = [
            event.run
            for event in captured
            if event.event_type == "workflow.execution_started" and event.run is not None
        ]

        root_workflow_run = next(run for run in workflow_runs if run.meta.get("flow_name") == "daily-news-root-flow")
        subflow_workflow_run = next(
            run for run in workflow_runs if run.meta.get("flow_name") == "daily-news-summary-sub-flow"
        )

        subflow_parent_chunk = next(
            event.run
            for event in captured
            if event.event_type == "chunk.started"
            and event.run is not None
            and event.run.run_id == subflow_workflow_run.parent_run_id
        )
        assert subflow_parent_chunk is not None
        assert subflow_parent_chunk.parent_run_id == root_workflow_run.run_id

        summarize_chunk = next(
            event.run
            for event in captured
            if event.event_type == "chunk.started"
            and event.run is not None
            and event.run.meta.get("chunk_name") == "summarize_candidate"
        )
        assert summarize_chunk is not None
        assert summarize_chunk.parent_run_id == subflow_workflow_run.run_id

        agent_turn_run = next(
            event.run
            for event in captured
            if event.event_type == "agent_turn.started" and event.run is not None
        )
        assert agent_turn_run is not None
        assert agent_turn_run.parent_run_id == summarize_chunk.run_id

        request_starts = [event.run for event in captured if event.event_type == "request.started" and event.run is not None]
        parent_ids = {run.parent_run_id for run in request_starts}
        assert summarize_chunk.run_id in parent_ids
        assert agent_turn_run.run_id in parent_ids

        model_request_runs = [
            event.run
            for event in captured
            if event.event_type == "model.request_started" and event.run is not None
        ]
        assert len(model_request_runs) >= 2
        assert all(run.parent_run_id in {request.run_id for request in request_starts} for run in model_request_runs)
    finally:
        Agently.event_center.unregister_hook(hook_name)
