"""
Step 1:
    > pip install streamlit==1.33.0 Agently>=3.0.1
Step 2:
    > streamlit run stream_output_in_streamlit.py
"""

import queue, threading, time
import streamlit as st
import Agently


def agent_chat_generator(agent, message, session_id):
    """reply generator"""
    reply_queue = queue.Queue()
    agent.active_session(session_id)

    @agent.on_event("delta")
    def on_delta(data):
        reply_queue.put_nowait(data)

    @agent.on_event("done")
    def on_done(data):
        reply_queue.put_nowait("$STOP")

    agent_thread = threading.Thread(target=agent.input(message).start)
    agent_thread.start()
    while True:
        reply = reply_queue.get()
        if reply == "$STOP":
            break
        for r in list(reply):
            time.sleep(0.01)  # for fluency output
            yield r
    agent_thread.join()
    agent.stop_session()


st.title("ChatBot based on Agently")

# init required params
required_params = ["current_model", "base_url", "api_key", "session_id", "agent_id", "message_list"]
for param in required_params:
    if param not in st.session_state:
        if param.endswith("_list"):
            st.session_state[param] = []
        elif param.endswith("_dict"):
            st.session_state[param] = {}
        else:
            st.session_state[param] = ""

# Display chat history
for message in st.session_state.message_list:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

################
## Sidebar ##
################

with st.sidebar:
    st.title("Settings")
    st.session_state.current_model = st.selectbox("Current Model", ["Kimi", "OpenAI", "Claude3"])
    st.session_state.base_url = st.text_input("Base URL", "")
    st.session_state.api_key = st.text_input("API Key", "", type="password")
    st.session_state.session_id = st.text_input("Session ID", "sess_1")
    st.session_state.agent_id = st.text_input("Agent ID", "demo_agent_1")

################
## Main Page ##
################

if prompt := st.chat_input("ask something..."):
    if not st.session_state.api_key:
        st.warning('Please enter API key!', icon='⚠')
    st.session_state.message_list.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        current_model = st.session_state.current_model
        api_key = st.session_state.api_key
        base_url = st.session_state.base_url
        # Get agent
        agent_factory = (
            Agently.AgentFactory()
            .set_settings("current_model", current_model)
            .set_settings(f"model.{current_model}.auth", {"api_key": api_key})
            .set_settings(f"model.{current_model}.url", base_url)
        )
        agent = agent_factory.create_agent(agent_id=st.session_state.agent_id)
        # Stream agent reply
        response = st.write_stream(agent_chat_generator(agent=agent,
                                                        message=prompt,
                                                        session_id=st.session_state.session_id))
    st.session_state.message_list.append({"role": "assistant", "content": response})
