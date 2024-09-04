import time

def gradio_app(app_connector, **kwargs):
    """
    Support Kwargs:
        multi_round (bool=True): Turn on or turn off multi round chat.
        interface (dict): Additional interface options dict.
        launch (dict): Additional launch options dict.
    """
    is_multi_round = kwargs.get("multi_round", True)
    is_fluency = kwargs.get("fluency", False)
    try:
        import gradio as gr
    except:
        raise Exception("[Application Connector] Package 'gradio' require to be installed. Use 'pip install gradio' to install.")
    def app_executor(message, history):
        if app_connector.message_handler:
            # Refresh binded agent event
            app_connector.refresh_binded_agent()
            # Format chat history
            chat_history = []
            if is_multi_round:
                for round in history:
                    if round[0]:
                        chat_history.append({ "role": "user", "content": round[0] })
                    if round[1]:
                        chat_history.append({ "role": "assistant", "content": round[1] })
            # Define generator event handlers
            app_connector.on("buffer", lambda data: { "yield": data })
            app_connector.on("done", lambda data: { "yield": data, "end": True })
            # Run message handler
            app_connector.run_message_handler(message, chat_history)
            # Get response from data generator
            try:
                for item in app_connector.data_generator.start():
                    if is_fluency:
                        time.sleep(0.01)
                    if item:
                        yield item
                app_connector.reset_data_generator()
                return
            except StopIteration:
                app_connector.reset_data_generator()
                return
        else:
            return "No Message Handler, use `.set_message_handler()` to set one."
    gr.ChatInterface(
        app_executor,
        title="Agently Gradio Chatbot",
        description="A Chatbot powered by Agently & Gradio",
        textbox=gr.Textbox(placeholder="Now let's talk..."),
        **(kwargs.get("interface", {}))
    ).launch(**(kwargs.get("launch", {})))