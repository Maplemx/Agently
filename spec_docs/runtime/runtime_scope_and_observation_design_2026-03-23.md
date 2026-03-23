# Agently Runtime Scope And Observation Design

Updated: 2026-03-23

## Why This Exists

Agently now has a runtime event bus and run lineage, but the original execution units were still too coarse:

- `request` was carrying both "one model/request pipeline" and "one complete agent turn"
- tool behavior produced its own runtime subtree without a clear place in the higher-level agent execution
- session changes were observable only as side effects, not as explicit runtime facts
- observation consumers had to infer structure from raw event names instead of relying on stable run scopes

This document defines the runtime scope hierarchy that observation, policy, and future multi-agent behavior should build on.

## Design Principles

1. `runtime` is the framework-level execution system.
2. `run` is one concrete execution instance.
3. Observation should primarily organize around run tree first, event stream second.
4. Stable execution scopes should be modeled as run kinds.
5. Long-lived ambient state such as `session` or `tenant` should not be forced into run lineage.
6. Temporary orchestration phases may still exist during migration, but should not become the long-term primary abstraction.

## Run Scope Hierarchy

### Stable Run Scopes

- `workflow_execution`
  One TriggerFlow execution instance.
- `agent_turn`
  One complete agent-facing turn initiated from `agent.start()` / `agent.async_start()` / related response getters.
- `request`
  One request pipeline execution.
- `model_request`
  One concrete model call attempt under a request.
- `action`
  One non-model executable action.

### Non-Run Scopes

- `session`
- `project`
- `workspace`
- `tenant`
- `environment`

These are scope metadata or event domains, not run kinds.

## Current Runtime Shape

The current migration target is:

```text
workflow_execution
  -> agent_turn
    -> request
      -> model_request
      -> tool_loop   (temporary orchestration scope during migration)
        -> workflow_execution
        -> action
```

Direct request usage remains valid:

```text
request
  -> model_request
```

Notes:

- `tool_loop` is still retained as an internal orchestration run for now because the tool planner currently uses an embedded TriggerFlow execution.
- Individual tool executions should now be represented as `action` runs rather than `tool_call`.
- Long term, `tool_loop` should be treated as a phase or orchestration detail rather than a primary runtime scope.

## Event Families

The preferred event families are:

- `workflow.*`
- `agent_turn.*`
- `request.*`
- `model.*`
- `action.*`
- `session.*`

### Implemented Runtime Families In This Iteration

- `agent_turn.started`
- `agent_turn.completed`
- `agent_turn.failed`
- `request.started`
- `request.completed`
- `request.failed`
- `prompt.built`
- `model.request_started`
- `model.requesting`
- `model.streaming`
- `model.completed`
- `model.meta`
- `model.failed`
- `model.request_failed`
- `model.retrying`
- `tool.loop_started`
- `tool.plan_ready`
- `tool.loop_completed`
- `tool.loop_failed`
- `action.started`
- `action.completed`
- `action.failed`
- `session.activated`
- `session.deactivated`
- `session.applied_to_request`
- `session.context_appended`
- `workflow.execution_started`
- `workflow.interrupt_raised`
- `workflow.execution_resumed`
- `workflow.stream_item_emitted`
- `workflow.result_set`
- `workflow.execution_completed`
- `workflow.execution_failed`

## Scope Ownership

### Agent

`BaseAgent` owns the `agent_turn` boundary.

That means:

- one user-visible `agent` call starts one `agent_turn`
- the `request` run should become a child of that turn
- `agent_turn` is the correct observation unit for "what this agent turn actually did"

### Request

`ModelRequest` owns the `request` run boundary.

That means:

- direct request usage can still start from `request`
- when called under `agent_turn`, request becomes a child run
- retries should not create new request runs

### Model

`ModelResponse` owns `model_request` attempt runs.

That means:

- each retry produces a new `model_request`
- prompt snapshot and request payload belong here
- streaming belongs here

### Tool / Action

`Tool` currently owns two layers:

- one temporary `tool_loop` orchestration run
- one `action` run per concrete tool execution

`action` should become the generic non-model execution abstraction for:

- tool calls
- KB retrieval
- internal module calls
- gateway send / receive
- HTTP / RPC / MCP integrations

### Session

`Session` should not be treated as a run.

Instead it should emit state-change or application events associated with the active request or turn.

## Observation Consumption Model

Observation should be organized in this order:

1. Filter by non-run scopes and search
   - project
   - flow name
   - session id
   - time range
   - keyword / prompt / ids
2. Build run tree from stable run scopes
3. Render detail blocks by selected run kind
4. Preserve raw event stream as the final debugging view

### Recommended Tree Nodes

- `workflow_execution`
- `agent_turn`
- `request`
- `model_request`
- `action`

### Recommended Detail Blocks

- `workflow_execution`
  - interrupts
  - stream items
  - result
  - child runs
- `agent_turn`
  - requests
  - actions
  - session effects
  - final output
- `request`
  - prompt / request lifecycle
  - model requests
  - actions
- `model_request`
  - prompt snapshot
  - request payload
  - streaming text
  - final response
  - provider/meta
- `action`
  - input
  - output
  - error
  - type / target / timing

## Migration Notes

The current implementation is intentionally transitional:

- `agent_turn` is now introduced at the public agent entrypoint.
- `action` replaces concrete tool-call runtime nodes.
- `tool_loop` is retained temporarily.
- `session` is still an event domain rather than a run domain.

Future cleanup should consider:

1. Automatically inheriting current execution run context when agent calls are made inside flow handlers.
2. Reducing `tool_loop` from a primary run kind to an orchestration detail.
3. Adding richer `session.*` events for reset/load/save/resize/memo updates.
4. Adding higher-level scope metadata for project/workspace/tenant/environment.
