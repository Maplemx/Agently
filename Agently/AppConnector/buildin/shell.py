def shell_app(app_connector, **kwargs):
    """
    Support Kwargs:
        user_name (str): Set user name to be displayed.
        assistant_name (dict): Set assistant name to be displayed.
    """
    if not app_connector.message_handler:
        raise Exception("No Message Handler, use `.set_message_handler()` to set one.")
    user_name = kwargs.get("user_name", "User")
    assistant_name = kwargs.get("assistant_name", "Assistant")
    message = ""
    chat_history = []
    while True:
        message = input(f"[{ user_name }]:")
        if message == "#exit":
            break
        # Define generator event handlers
        app_connector.on("delta", lambda data: { "yield": data })
        app_connector.on("done", lambda data: { "end": True })
        # Run message handler
        app_connector.run_message_handler(message, chat_history)
        print(f"[{ assistant_name }]:")
        buffer = ""
        try:
            for item in app_connector.data_generator.start():
                if item:
                    print(item, end="")
                    buffer += item
            chat_history.append({ "role": "user", "content": message })
            chat_history.append({ "role": "assistant", "content": buffer })
            app_connector.reset_data_generator()
            continue
        except StopIteration:
            app_connector.reset_data_generator()
            continue