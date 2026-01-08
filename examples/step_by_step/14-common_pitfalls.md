# Common Pitfalls & FAQs (Agently Dev)

## 1) Stream hangs or no output
- Symptom: terminal appears stuck after input.
- Cause: using sync generators inside an async context, or `get_runtime_stream(..., timeout=None)` without `stop_stream()`.
- Fix:
  - In async handlers, use `get_async_generator(...)` and `async for`.
  - Call `stop_stream()` when you want the runtime stream to end.

## 1.1) Streaming output labels spam
- Symptom: every token prints its own label (e.g., repeated `[thinking]`).
- Cause: printing labels on every delta.
- Fix: print the label once, then append deltas on the same line; add a newline on completion.

## 1.2) Streaming inside async loop throws `asyncio.run` error
- Symptom: `asyncio.run() cannot be called from a running event loop`.
- Cause: using sync `get_response().get_generator(...)` inside an async handler.
- Fix: use `request.get_async_generator(...)` with `async for`.

## 2) TriggerFlow returns `None`
- Symptom: `flow.start()` returns `None`.
- Cause: no `end()` or no `set_result()` on the chain that should produce output.
- Fix:
  - Use `end()` on the main chain, or
  - call `execution.set_result(...)` explicitly.

## 2.1) end() placed on the wrong chain
- Symptom: flow returns the wrong value or ends too early.
- Cause: `end()` attached to START or the wrong branch.
- Fix: attach `end()` to the chain that should produce the default result; `when()` branches need explicit `end()` or `set_result()`.

## 3) when() branch does not finalize result
- Symptom: `start(wait_for_result=True)` times out.
- Cause: `when()` branches are event-driven and do not set result by default.
- Fix: add `.end()` on that branch or `set_result()`.

## 4) Concurrency wrapper issues
- Symptom: wrong handler called in batch/for_each.
- Cause: closure binding in loops.
- Fix: bind handler per chunk (factory or default argument).

## 5) Flow data vs runtime data
- Symptom: data leaks across executions.
- Cause: `flow_data` is global.
- Fix: use `runtime_data` for per-execution state.

## 6) Wrong entry point in loop flows
- Symptom: input never arrives or loop blocks.
- Cause: starting with `to(get_input)` and waiting on events that are never emitted.
- Fix: emit a loop event (e.g., `Loop`) at start, then `when("Loop") -> get_input`.

## 6) Instant stream is noisy
- Symptom: each token prints a label.
- Fix: print label once, then stream tokens on the same line; print newline on completion.

## 7) Tools not called or wrong tool
- Symptom: model ignores tools or calls invalid tool.
- Fix:
  - ensure tool names and schemas are clear in `.output()` or `.info()`
  - keep tool list concise

## 8) Knowledge base rebuild every turn
- Symptom: repeated slow initialization.
- Fix: build KB once and reuse (e.g., cached collection in outer scope).

## 9) httpx INFO spam
- Symptom: noisy httpx/httpcore logs.
- Fix: set `runtime.httpx_log_level` to `WARNING` or `ERROR`.

## 10) Settings not applied as expected
- Symptom: model config seems ignored.
- Fix:
  - call `Agently.set_settings(...)` before creating agents
  - check runtime mappings (`debug` toggles multiple flags)
