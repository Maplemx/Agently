import threading
from ..utils import DataGenerator, DataOps
from .buildin import gradio_app, streamlit_app, shell_app

class AppConnector(object):
    def __init__(
            self,
            *,
            app_name:str="gradio",
            message_handler:callable=None,
            binded_agent:object=None,
        ):
        self.app_name = app_name
        self.message_handler = message_handler
        self.message_handler_thread = None
        self.binded_agent = binded_agent
        self.buffer = ""
        self.app_dict = {
            "gradio": gradio_app,
            "streamlit": streamlit_app,
            "shell": shell_app,  
        }
        self.runtime = DataOps()
        self.data_generator = DataGenerator()
    
    def register_app(self, type_name:str, app:callable):
        self.app_dict.update({ type_name: app })
        return self
    
    def use_app(self, app_name:str):
        self.app_name = app_name
        return self
    
    def set_message_handler(self, message_handler: callable):
        self.message_handler = message_handler
        return self
    
    def run_message_handler(self, *args, **kwargs):
        self.message_handler_thread = threading.Thread(
            target=self.message_handler,
            args=args,
            kwargs=kwargs,
        )
        self.message_handler_thread.start()
        return self
    
    def bind_agent(self, agent):
        self.binded_agent = agent
        if self.message_handler == None:
            self.set_message_handler(
                lambda message, chat_history: agent.chat_history(chat_history).input(message).start()
            )
        return self
    
    def refresh_binded_agent(self):
        if self.binded_agent:
            @self.binded_agent.on_event("delta")
            def delta_handler(data):
                self.emit_delta(data)
            @self.binded_agent.on_event("done")
            def delta_handler(data):
                self.emit_done(data)
        return self
    
    def emit(self, event: str, data: any):
        self.data_generator.event.emit(event, data)
        return self

    def emit_delta(self, delta:str=None):
        self.buffer += delta if delta else ""
        self.emit("delta", delta)
        self.emit("buffer", self.buffer)
        return self
    
    def emit_buffer(self, buffer:str=None):
        self.buffer = buffer if buffer else ""
        self.emit("buffer", self.buffer)
        return self
    
    def emit_done(self, final_result:str=None):
        self.emit("done", final_result if final_result else self.buffer)
        self.buffer = ""
        return self

    def on(self, event:str, handler:callable):
        self.data_generator.event.on(event, handler)
        return self
    
    def reset_data_generator(self):
        self.data_generator = DataGenerator()
        return self

    def run(self, app_name:str=None, **kwargs):
        app_name = app_name or self.app_name
        self.app_dict[app_name](self, **kwargs)
        if self.message_handler_thread:
            self.message_handler_thread.join()
            self.message_handler_thread = None