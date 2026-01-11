# AI Coding with Agently: Build Functional Workflows

This guide shows a practical pattern for using Agently to build working AI code—especially multi‑turn flows that collect structured information from users.

## 1) Start with explicit workflow goals
Define the outcome in plain language and in schema terms.

**Example goal:** collect pre‑order information from a user in multiple turns.

```python
FORM_FIELDS = [
    {"key": "full_name", "desc": "customer full name"},
    {"key": "email", "desc": "customer email"},
    {"key": "product", "desc": "product name"},
    {"key": "quantity", "desc": "order quantity"},
    {"key": "delivery_city", "desc": "delivery city"},
]
```

## 2) Use structured prompts to keep control
Prefer `input / instruct / info / output` instead of a single prompt string.

```python
result = (
    agent.input(user_answer)
    .instruct("Extract the user answer for the requested field.")
    .info({"field_key": field["key"], "field_desc": field["desc"]})
    .output({field["key"]: ("str", field["desc"])})
    .start(ensure_keys=[field["key"]])
)
```

## 3) Add a role that controls tone and purpose
Set a stable role so the assistant behaves consistently.

```python
agent.role(
    "You are a friendly customer experience assistant at a startup."
    " Introduce yourself and explain the interview purpose."
    " Respond with empathy when users are unsure.",
    always=True,
)
```

## 4) Build an interview loop with intent routing
First classify intent, then decide how to respond.

```python
intent = classify_intent(agent, field, user_input)
if intent == "exit":
    return
if intent == "ask_suggestion" and field["key"] == "product":
    show_product_suggestions()
if intent in {"unknown", "refuse"}:
    clarify_or_skip()
```

**Common intents to handle:**
- `answer`: normal answer
- `unknown`: “not sure”, “don’t know”
- `refuse`: “no”, “prefer not to say”
- `ask_suggestion`: user asks for help
- `exit`: “bye”, “stop”

## 5) Validate and retry before storing
Store only clean values and skip after a retry limit.

```python
is_valid, reason = validate_value(field_key, value)
if not is_valid:
    retry_question = generate_question(agent, field, form_data, hint=reason)
```

## 6) Support reset and graceful exit
Users should be able to restart or stop anytime.

```python
if user_input.lower() == "reset":
    reset_form(form_data)
    agent.reset_chat_history()
```

## 7) Confirm missing items before finalizing
If fields are skipped, ask if they want to continue.

```python
if skipped_fields:
    ask_to_continue()
```

## Example reference
See a full implementation in:
`examples/preorder_interview_reset_form.py`

This example includes role settings, startup intro, intent routing, validation, suggestions, and reset handling.
