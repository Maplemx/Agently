from agently import Agently


Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
    },
)


FORM_FIELDS = [
    {
        "key": "full_name",
        "question": "What is your full name?",
        "desc": "customer full name",
    },
    {
        "key": "email",
        "question": "What email should we use for updates?",
        "desc": "customer email",
    },
    {
        "key": "product",
        "question": "Which product would you like to pre-order?",
        "desc": "product name",
    },
    {
        "key": "quantity",
        "question": "How many units do you want to reserve?",
        "desc": "order quantity",
    },
    {
        "key": "delivery_city",
        "question": "Which city should we deliver to?",
        "desc": "delivery city",
    },
]

PRODUCT_SUGGESTIONS = [
    "Agently Smart Watch",
    "Agently Home Hub",
    "Agently Travel Charger",
]

ROLE_SETTINGS = (
    "You are a friendly customer experience assistant at a startup. "
    "You introduce yourself, explain the purpose of the interview, "
    "and respond with empathy when users feel unsure or frustrated."
)


def reset_form(form_data: dict) -> None:
    form_data.clear()


def next_pending_field(form_data: dict, skipped_fields: set[str]) -> dict | None:
    for field in FORM_FIELDS:
        if field["key"] not in form_data and field["key"] not in skipped_fields:
            return field
    return None


def generate_question(agent, field: dict, form_data: dict, hint: str | None = None) -> str:
    result = (
        agent.input("Generate the next interview question.")
        .instruct(
            "Ask a friendly, concise question to collect the field." " Avoid repeating details already collected."
        )
        .info(
            {
                "field_key": field["key"],
                "field_desc": field["desc"],
                "field_default_question": field["question"],
                "current_form_data": form_data,
                "hint": hint,
            }
        )
        .output({"question": ("str", "next question")})
        .start(ensure_keys=["question"])
    )
    return result["question"].strip()


def generate_startup_message(agent) -> str:
    result = (
        agent.input("Generate a short welcome message.")
        .instruct(
            "Introduce yourself, mention you are a startup team member, "
            "and explain you are collecting pre-order details. "
            "Keep it warm and under 2 sentences."
        )
        .output({"message": ("str", "startup welcome message")})
        .start(ensure_keys=["message"])
    )
    return result["message"].strip()


def parse_answer(agent, field: dict, user_answer: str) -> str:
    result = (
        agent.input(user_answer)
        .instruct("Extract the user answer for the requested field." " Return plain text only.")
        .info(
            {
                "field_key": field["key"],
                "field_desc": field["desc"],
            }
        )
        .output({field["key"]: ("str", field["desc"])})
        .start(ensure_keys=[field["key"]])
    )
    return result[field["key"]].strip()


def classify_intent(agent, field: dict, user_answer: str) -> str:
    result = (
        agent.input(user_answer)
        .instruct(
            "Classify the user's intent for this field." " Use one of: answer, unknown, refuse, exit, ask_suggestion."
        )
        .info(
            {
                "field_key": field["key"],
                "field_desc": field["desc"],
                "allowed_intents": [
                    "answer",
                    "unknown",
                    "refuse",
                    "exit",
                    "ask_suggestion",
                ],
            }
        )
        .output({"intent": ("str", "intent label")})
        .start(ensure_keys=["intent"])
    )
    intent = result["intent"].strip().lower()
    if intent not in {
        "answer",
        "unknown",
        "refuse",
        "exit",
        "ask_suggestion",
    }:
        return "answer"
    return intent


def validate_value(field_key: str, value: str) -> tuple[bool, str | None]:
    if not value:
        return False, "It looks empty."
    if field_key == "email":
        if "@" not in value or "." not in value:
            return False, "Please provide a valid email address."
    if field_key == "quantity":
        if not value.isdigit() or int(value) <= 0:
            return False, "Please provide a positive number."
    return True, None


def normalize_yes_no(user_input: str) -> str:
    normalized = user_input.strip().lower()
    if normalized in {"yes", "y", "sure", "ok", "okay"}:
        return "yes"
    if normalized in {"no", "n", "stop", "exit", "quit"}:
        return "no"
    return "unknown"


def wants_reset_or_exit(user_input: str) -> str | None:
    normalized = user_input.strip().lower()
    if normalized == "reset":
        return "reset"
    if normalized in {"bye", "exit", "quit", "stop"}:
        return "exit"
    return None


def interview_with_reset_demo():
    agent = Agently.create_agent()
    agent.role(ROLE_SETTINGS, always=True)
    form_data: dict[str, str] = {}
    skipped_fields: set[str] = set()
    attempts: dict[str, int] = {}

    startup_message = generate_startup_message(agent)
    print(f"[assistant] {startup_message}")
    print("Type 'reset' anytime to start over.\n")

    while True:
        pending_field = next_pending_field(form_data, skipped_fields)
        if pending_field is None:
            if skipped_fields:
                skipped_list = ", ".join(sorted(skipped_fields))
                print("\n[assistant] We still need: " f"{skipped_list}. Continue? (yes/no)")
                continue_input = input("[user] ").strip()
                if wants_reset_or_exit(continue_input) == "reset":
                    reset_form(form_data)
                    skipped_fields.clear()
                    attempts.clear()
                    agent.reset_chat_history()
                    print("[system] Form reset. Let's start again.\n")
                    continue
                if normalize_yes_no(continue_input) != "yes":
                    print("\n[assistant] No problem. See you next time!")
                    return
                skipped_fields.clear()
                continue
            break

        field_key = pending_field["key"]
        question = generate_question(agent, pending_field, form_data)
        print(f"[assistant] {question}")
        user_input = input("[user] ").strip()

        reset_or_exit = wants_reset_or_exit(user_input)
        if reset_or_exit == "reset":
            reset_form(form_data)
            skipped_fields.clear()
            attempts.clear()
            agent.reset_chat_history()
            print("[system] Form reset. Let's start again.\n")
            continue
        if reset_or_exit == "exit":
            print("\n[assistant] Thanks for stopping by. Goodbye!")
            return

        intent = classify_intent(agent, pending_field, user_input)
        if intent == "exit":
            print("\n[assistant] Thanks for stopping by. Goodbye!")
            return

        if intent == "ask_suggestion" and field_key == "product":
            suggestion_list = ", ".join(PRODUCT_SUGGESTIONS)
            print("[assistant] Here are some options: " f"{suggestion_list}. Which one fits?")
            suggestion_input = input("[user] ").strip()
            reset_or_exit = wants_reset_or_exit(suggestion_input)
            if reset_or_exit == "reset":
                reset_form(form_data)
                skipped_fields.clear()
                attempts.clear()
                agent.reset_chat_history()
                print("[system] Form reset. Let's start again.\n")
                continue
            if reset_or_exit == "exit":
                print("\n[assistant] Thanks for stopping by. Goodbye!")
                return
            user_input = suggestion_input

        if intent in {"unknown", "refuse"}:
            attempts[field_key] = attempts.get(field_key, 0) + 1
            if attempts[field_key] >= 2:
                skipped_fields.add(field_key)
                print("[assistant] Thanks for sharing. We'll skip this for now.\n")
                continue
            clarification = generate_question(
                agent,
                pending_field,
                form_data,
                hint="The user was unsure or refused. Ask gently if they can share it.",
            )
            print(f"[assistant] {clarification}")
            follow_up = input("[user] ").strip()
            reset_or_exit = wants_reset_or_exit(follow_up)
            if reset_or_exit == "reset":
                reset_form(form_data)
                skipped_fields.clear()
                attempts.clear()
                agent.reset_chat_history()
                print("[system] Form reset. Let's start again.\n")
                continue
            if reset_or_exit == "exit":
                print("\n[assistant] Thanks for stopping by. Goodbye!")
                return
            user_input = follow_up

        value = parse_answer(agent, pending_field, user_input)
        is_valid, reason = validate_value(field_key, value)
        if not is_valid:
            attempts[field_key] = attempts.get(field_key, 0) + 1
            if attempts[field_key] >= 2:
                skipped_fields.add(field_key)
                print("[assistant] No worries. We'll skip this for now.\n")
                continue
            retry_question = generate_question(
                agent,
                pending_field,
                form_data,
                hint=reason,
            )
            print(f"[assistant] {retry_question}")
            retry_input = input("[user] ").strip()
            reset_or_exit = wants_reset_or_exit(retry_input)
            if reset_or_exit == "reset":
                reset_form(form_data)
                skipped_fields.clear()
                attempts.clear()
                agent.reset_chat_history()
                print("[system] Form reset. Let's start again.\n")
                continue
            if reset_or_exit == "exit":
                print("\n[assistant] Thanks for stopping by. Goodbye!")
                return
            value = parse_answer(agent, pending_field, retry_input)
            is_valid, _ = validate_value(field_key, value)
            if not is_valid:
                skipped_fields.add(field_key)
                print("[assistant] Thanks for trying. We'll skip this for now.\n")
                continue

        form_data[field_key] = value
        agent.add_chat_history({"role": "assistant", "content": question})
        agent.add_chat_history({"role": "user", "content": user_input})

    if next_pending_field(form_data, skipped_fields) is None:
        print("\n[assistant] Thanks! Here is the pre-order info collected:")
        for key, value in form_data.items():
            print(f"- {key}: {value}")
        if skipped_fields:
            skipped_list = ", ".join(sorted(skipped_fields))
            print(f"\n[assistant] Missing: {skipped_list}")


interview_with_reset_demo()
