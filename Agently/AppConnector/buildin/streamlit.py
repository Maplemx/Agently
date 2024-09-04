import os
import time
import subprocess

def streamlit_app(app_connector, **kwargs):
    is_multi_round = kwargs.get("multi_round", True)
    is_fluency = kwargs.get("fluency", False)
    st = app_connector.runtime.get("package.streamlit")
    if not st:
        try:
            import streamlit as st
            app_connector.runtime.set("package.streamlit", st)
        except:
            raise Exception("[Application Connector] Package 'streamlit' require to be installed. Use 'pip install streamlit' to install.")
    def get_chat_response():
        for item in app_connector.data_generator.start():
            if is_fluency:
                for char in list(item):
                    time.sleep(0.01)
                    yield char
            else:
                yield item
    st.title("A Chatbot powered by Agently & Streamlit")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    message = st.chat_input("Now let's talk...")
    if message:
        if not app_connector.message_handler:
            st.warning("No Message Handler, use `.set_message_handler()` to set one.", icon="⚠️")
        
        # Refresh binded agent event
        app_connector.refresh_binded_agent()
        # Define generator event handlers
        app_connector.on("delta", lambda data: { "yield": data })
        app_connector.on("done", lambda data: { "end": True })
        with st.chat_message("user"):
            st.markdown(message)
        st.session_state.chat_history.append({"role": "user", "content": message})
        with st.spinner("Processing..."):
            with st.chat_message("assisitant"):
                if is_multi_round:
                    app_connector.run_message_handler(
                        message,
                        st.session_state.chat_history[:-1]
                        if len(st.session_state.chat_history) > 0
                        else []
                    )
                else:
                    app_connector.run_message_handler(message, [])
                response_generator = get_chat_response()
                response = st.write_stream(response_generator)
                st.session_state.chat_history.append({ "role": "assistant", "content": response })
                app_connector.reset_data_generator()