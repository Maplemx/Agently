# Agently Utils Guide (Agent-Readable)

Use this as a compact, agent-oriented guide to the utilities in `agently/utils`. It is intentionally brief and practical.

## Quick Map (TL;DR)
- data shaping: `DataFormatter`, `RuntimeData`, `SerializableRuntimeData`, `Settings`
- path and JSON helpers: `DataLocator`, `DataPathBuilder`, `StreamingJSONCompleter`, `StreamingJSONParser`
- async/sync bridging: `FunctionShifter`, `GeneratorConsumer`
- dynamic deps: `LazyImport`
- storage: `Storage`, `AsyncStorage`
- misc: `Logger`, `Messenger`, `PythonSandbox`
- legacy: `old_RuntimeData` (avoid unless you must keep backward behavior)

## Utilities

### DataFormatter
Purpose: normalize complex values into safe, serializable, or string forms, and do placeholder substitution.

Key methods:
- `sanitize(value, remain_type=False)`: convert complex objects into JSON-ish values. Handles `datetime`, `RuntimeData`, `pydantic.BaseModel`, and typing constructs like `list[T]`, `Union`, `Literal`.
- `to_str_key_dict(value, value_format=None, default_key=None, default_value=None)`: ensure dict keys are strings and values optionally sanitized or stringified. If input is not a dict, can wrap with `default_key`.
- `from_schema_to_kwargs_format(schema)`: convert JSON Schema object fields into Agently kwargs-style `(type, desc)` mapping.
- `substitute_placeholder(obj, variable_mappings, placeholder_pattern=None)`: recursive replace `${key}` placeholders in strings, dicts, lists, sets, tuples.

When to use:
- Before logging/serialization.
- When building structured prompts from schemas.
- When injecting env variables into settings or prompts.

### DataLocator
Purpose: locate values by path, and extract JSON blocks from mixed text.

Key methods:
- `locate_path_in_dict(dict, path, style="dot"|"slash", default=None)`: safe deep lookup with `a.b[0]` or `/a/b/0` styles.
- `locate_all_json(text)`: scan text and return all JSON-like blocks.
- `locate_output_json(text, output_prompt_dict)`: pick the most likely JSON block matching your output schema.

When to use:
- Parsing LLM responses that mix text + JSON.
- Robust extraction for streaming parsers.

### DataPathBuilder
Purpose: convert and reason about dot/slash paths, and extract expected parsing paths from a schema-like dict.

Key methods:
- `build_dot_path(keys)`, `build_slash_path(keys)`
- `convert_dot_to_slash(dot_path)`, `convert_slash_to_dot(slash_path)`
- `extract_possible_paths(schema, style="dot")`: find all possible paths.
- `extract_parsing_key_orders(schema, style="dot")`: paths in definition order (used by streaming parser).
- `get_value_by_path(data, path, style="dot")`: retrieve values, supports `[*]` wildcard expansion.

When to use:
- Streaming JSON parsing with ordered fields.
- Mapping UI updates to schema paths.

### FunctionShifter
Purpose: bridge sync/async code and run async work safely from sync contexts.

Key methods:
- `syncify(func)`: wrap an async function so it can be called in sync code. Uses `asyncio.run` or a thread when a loop is running.
- `asyncify(func)`: wrap a sync function so it can be awaited via `asyncio.to_thread`.
- `future(func)`: return a `Future` for the function execution; ensures there is a loop.
- `syncify_async_generator(async_gen)`: consume an async generator from sync code via a background thread.
- `auto_options_func(func)`: drop extra kwargs that the function does not accept.

When to use:
- Tool functions that may be sync or async.
- Adapters between streaming generators and sync APIs.

### GeneratorConsumer
Purpose: fan out a generator or async generator to multiple consumers, replay history, and handle errors.

Usage:
- Wrap a generator, then call `get_async_generator()` for multiple async consumers or `get_generator()` for sync.
- `get_result()` waits for completion and returns full history.
- `close()` cancels and notifies listeners.

When to use:
- Broadcast streaming output to multiple subscribers.
- Merge history + live updates reliably.

### LazyImport
Purpose: import optional deps and optionally auto-install via pip with version constraints.

Key methods:
- `from_import(from_package, target_modules, auto_install=True, version_constraint=None, install_name=None)`
- `import_package(package_name, auto_install=True, version_constraint=None, install_name=None)`

Notes:
- This prompts for installation in interactive use; plan for non-interactive runtime accordingly.

### Logger
Purpose: create a consistent logger with optional uvicorn integration.

Key pieces:
- `create_logger(app_name="Agently", log_level="INFO")` returns `AgentlyLogger` with `raise_error` helper.

### Messenger
Purpose: convenience wrapper for event center messaging.

Key method:
- `create_messenger(module_name)` delegates to `agently.base.event_center`.

### PythonSandbox
Purpose: execute small snippets safely with restricted builtins and whitelisted return types.

Key behaviors:
- `run(code)` executes in a sandbox; raises if a return type is not in `allowed_return_types`.
- `preset_objects` are wrapped to block private attributes and enforce safe return types.

When to use:
- Run short user-defined expressions or filters with safety checks.

### RuntimeData / RuntimeDataNamespace
Purpose: runtime-scoped hierarchical data with inheritance, dot-path access, and merge-friendly set semantics.

Key behaviors:
- `get(key, default=None, inherit=True)`: inherited view by default.
- `set` and `__setitem__` merge dict/list/set values rather than replace (unless you use `cover=True` internally).
- dot-path access: `data["a.b.c"]`.
- `namespace("path")` returns a namespace view.
- `dump("json"|"yaml"|"toml")`, `load(...)` support.

When to use:
- Store workflow state, memo, runtime configs.

### SerializableRuntimeData / SerializableRuntimeDataNamespace
Purpose: same API as `RuntimeData` but value types restricted to JSON-serializable shapes.

When to use:
- Settings and serialized runtime state.

### Settings / SettingsNamespace
Purpose: settings with mapping shortcuts and env substitution.

Key behaviors:
- `register_path_mappings("short", "actual.path")`: alias keys.
- `register_kv_mappings("key", "value", actual_settings)`: map a key+value to a settings dict.
- `set_settings(key, value, auto_load_env=False)`: apply mappings and optionally expand `${ENV.X}`.

When to use:
- Global or per-agent configuration with shortcuts.

### Storage / AsyncStorage
Purpose: simple SQLModel-based persistence with sync/async APIs.

Key behaviors:
- requires `sqlmodel`, `sqlalchemy`, `aiosqlite` via `LazyImport`.
- `set(obj|list)` merges into DB.
- `get(model, where=..., first=False, limit=..., offset=..., order_by=...)`.
- `create_tables()` calls `SQLModel.metadata.create_all`.

When to use:
- local state persistence for agents or tools.

### StreamingJSONCompleter
Purpose: complete partial JSON strings by closing open strings, comments, or brackets.

Key method:
- `append(data)` then `complete()` to get best-effort JSON.

When to use:
- streaming LLM output where JSON is partial.

### StreamingJSONParser
Purpose: parse streaming JSON and emit incremental updates (`delta`) and completion events (`done`).

Key behaviors:
- Uses `DataLocator` + `StreamingJSONCompleter` to find and parse JSON in noisy streams.
- Tracks schema order via `DataPathBuilder.extract_parsing_key_orders`.
- `parse_chunk(chunk)` yields `StreamingData` events.
- `parse_stream(chunk_stream)` yields events and finalizes at end.

When to use:
- UI streaming updates for structured output.