from agently import Agently
from agently.core import Session

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
    },
)

agent = Agently.create_agent()


def basic_session_on_off():
    print("\n=== Example 1: Session On / Off ===")
    agent.activate_session(session_id="demo_on_off")

    print("[Ask to remember]")
    agent.input("Remember this: I need to buy eggs tomorrow.").streaming_print()

    print("[Session ON]")
    agent.input("What should I buy tomorrow?").streaming_print()

    agent.deactivate_session()
    print("[Session OFF]")
    agent.input("What should I buy tomorrow?").streaming_print()


# basic_session_on_off()


def session_isolation_by_id():
    print("\n=== Example 2: Session Isolation by ID ===")
    agent.activate_session(session_id="trip_a")
    agent.input("Remember this trip note: destination is Tokyo.").streaming_print()

    agent.activate_session(session_id="trip_b")
    agent.input("Remember this trip note: destination is Paris.").streaming_print()

    print("[Check trip_b]")
    agent.input("What is my destination?").streaming_print()

    agent.activate_session(session_id="trip_a")
    print("[Check trip_a]")
    agent.input("What is my destination?").streaming_print()


# session_isolation_by_id()


def session_record_with_input_reply_keys():
    print("\n=== Example 3: Record With input_keys/reply_keys (.info + .input) ===")
    agent.activate_session(session_id="demo_key_record")
    agent.set_settings("session.input_keys", ["info.task", "info.style", "input.lang"])
    agent.set_settings("session.reply_keys", ["summary", "keywords"])

    result = (
        agent.info(
            {
                "task": "Summarize Agently in one sentence.",
                "style": "technical",
            }
        )
        .input({"lang": "en", "extra": "ignore_me"})
        .output(
            {
                "summary": (str,),
                "keywords": [(str,)],
                "extra": (str,),
            }
        )
        .get_data()
    )
    print("[Parsed Result]")
    print(result)
    assert agent.activated_session is not None
    print("[Recorded Session History]")
    for idx, message in enumerate(agent.activated_session.full_context):
        print(f"{idx + 1}. {message.role}:\n{message.content}")

    # Reset to default recording behavior for next examples.
    agent.set_settings("session.input_keys", None)
    agent.set_settings("session.reply_keys", None)


# session_record_with_input_reply_keys()


def session_export_and_restore():
    print("\n=== Example 4: Export and Restore Session ===")
    agent.activate_session(session_id="demo_export")
    agent.input("Remember this recovery code: X-2025-ABCD").streaming_print()

    assert agent.activated_session is not None
    exported_json = agent.activated_session.get_json_session()
    print("[Exported JSON Preview]")
    print(exported_json)

    restored = Session(settings=agent.settings)
    restored.load_json_session(exported_json)
    restored_id = "demo_export_restored"
    restored.id = restored_id
    agent.sessions[restored_id] = restored
    agent.activate_session(session_id=restored_id)

    print("[Restored Session Check]")
    agent.input("What recovery code did I ask you to remember?").streaming_print()


# session_export_and_restore()


def session_custom_handlers():
    print("\n=== Example 5: Custom Session Handlers ===")
    agent.activate_session(session_id="demo_custom_handlers")
    assert agent.activated_session is not None
    session = agent.activated_session

    def analysis_handler(full_context, context_window, memo, session_settings):
        _ = full_context
        _ = memo
        _ = session_settings
        if len(context_window) > 2:
            return "keep_last_two"
        return None

    def keep_last_two_handler(full_context, context_window, memo, session_settings):
        _ = full_context
        _ = memo
        _ = session_settings
        return None, list(context_window[-2:]), {"strategy": "keep_last_two"}

    session.register_analysis_handler(analysis_handler)
    session.register_resize_handler("keep_last_two", keep_last_two_handler)

    agent.add_chat_history({"role": "user", "content": "turn-1"})
    agent.add_chat_history({"role": "assistant", "content": "turn-2"})
    agent.add_chat_history({"role": "user", "content": "turn-3"})
    agent.add_chat_history({"role": "assistant", "content": "turn-4"})

    print("[Full Context]")
    for idx, message in enumerate(session.full_context):
        print(f"{idx + 1}. {message.role}: {message.content}")

    print("[Context Window After Custom Handler]")
    for idx, message in enumerate(session.context_window):
        print(f"{idx + 1}. {message.role}: {message.content}")

    print("[Memo]")
    print(session.memo)


# session_custom_handlers()


def session_custom_handlers_with_real_request():
    print("\n=== Example 6: Custom Handlers With Real Request ===")
    agent.activate_session(session_id="demo_custom_handlers_live")
    assert agent.activated_session is not None
    session = agent.activated_session

    def analysis_handler(full_context, context_window, memo, session_settings):
        _ = full_context
        _ = memo
        _ = session_settings
        if len(context_window) > 4:
            return "keep_last_four"
        return None

    def keep_last_four_handler(full_context, context_window, memo, session_settings):
        _ = full_context
        _ = memo
        _ = session_settings
        kept = list(context_window[-4:])
        return None, kept, {"strategy": "keep_last_four", "kept_count": len(kept)}

    session.register_analysis_handler(analysis_handler)
    session.register_resize_handler("keep_last_four", keep_last_four_handler)

    print("[Turn 1]")
    agent.input("Remember my favorite city is Chengdu.").streaming_print()

    print("[Turn 2]")
    agent.input("Also remember my favorite food is hotpot.").streaming_print()

    print("[Turn 3]")
    agent.input("What city and food did I ask you to remember?").streaming_print()

    print("[Session State]")
    print(f"full_context: {len(session.full_context)}")
    print(f"context_window: {len(session.context_window)}")
    print(f"memo: {session.memo}")


# session_custom_handlers_with_real_request()


def session_custom_handlers_with_memo_in_real_request():
    print("\n=== Example 7: Custom Handlers With Memo In Real Request ===")
    agent.activate_session(session_id="demo_custom_handlers_with_memo")
    assert agent.activated_session is not None
    session = agent.activated_session

    def analysis_handler(full_context, context_window, memo, session_settings):
        _ = full_context
        _ = memo
        _ = session_settings
        if len(context_window) > 4:
            return "keep_last_four"
        else:
            return None

    async def keep_last_four_handler(full_context, context_window, memo, session_settings):
        _ = full_context
        _ = session_settings
        kept = list(context_window[-4:])
        memo_request = agent.create_temp_request()
        (
            memo_request.input({"messages": context_window[:-4], "history_memo": memo})
            .instruct("Recreate key points memo dict of {input.messages} and {input.history_memo}")
            .output(
                {
                    "key_points": {
                        "<point_title>": (str, "point content"),
                        "...": "...",
                    }
                }
            )
        )
        new_memo = await memo_request.async_start(ensure_keys=["key_points"])
        return None, kept, new_memo["key_points"]

    session.register_analysis_handler(analysis_handler)
    session.register_resize_handler("keep_last_four", keep_last_four_handler)

    print("[Turn 1]")
    agent.input("Remember my favorite city is Chengdu.").streaming_print()

    print("[Turn 2]")
    agent.input("Also remember my favorite food is hotpot.").streaming_print()

    print("[Turn 3]")
    agent.input("What city and food did I ask you to remember?").streaming_print()

    print("[Session State]")
    print(f"full_context: {len(session.full_context)}")
    print(f"context_window: {len(session.context_window)}")
    print(f"memo: {session.memo}")


session_custom_handlers_with_memo_in_real_request()
