from .llm_request import\
    prepare_request_data_gpt, request_gpt, streaming_gpt, handle_response_gpt,\
    prepare_request_data_minimax, request_minimax, streaming_minimax, handle_response_minimax,\
    prepare_request_data_spark, request_spark, streaming_spark, handle_response_spark,\
    prepare_request_data_wenxin, request_wenxin, streaming_wenxin, handle_response_wenxin

def update_process(work_node_management):
    result = work_node_management\
        .set_process("prepare_request_data", prepare_request_data_gpt, "GPT")\
        .set_process("request_llm", request_gpt, "GPT")\
        .set_process("streaming_llm", streaming_gpt, "GPT")\
        .set_process("handle_response", handle_response_gpt, "GPT")\
        .set_process("prepare_request_data", prepare_request_data_minimax, "MiniMax")\
        .set_process("request_llm", request_minimax, "MiniMax")\
        .set_process("streaming_llm", streaming_minimax, "MiniMax")\
        .set_process("handle_response", handle_response_minimax, "MiniMax")\
        .set_process("prepare_request_data", prepare_request_data_spark, "Spark")\
        .set_process("request_llm", request_spark, "Spark")\
        .set_process("streaming_llm", streaming_spark, "Spark")\
        .set_process("handle_response", handle_response_spark, "Spark")\
        .set_process("prepare_request_data", prepare_request_data_wenxin, "wenxin")\
        .set_process("request_llm", request_wenxin, "wenxin")\
        .set_process("streaming_llm", streaming_wenxin, "wenxin")\
        .set_process("handle_response", handle_response_wenxin, "wenxin")\
        .set_runtime_ctx({
            "minimax_bot_name": {
                "layer": "agent",
                "alias": { "set": "set_minimax_bot_name" },
                "default": "BOT",
            },
            "minimax_user_name": {
                "layer": "agent",
                "alias": { "set": "set_minimax_user_name" },
                "default": "USER",
            },
            "wx_model_name": {
                "layer": "agent",
                "alias": { "set": "set_wx_model_name" },
                "default": "qianfan_chinese_llama_2_7b",
            },
            "wx_model_type": {
                "layer": "agent",
                "alias": { "set": "set_wx_model_type" },
                "default": "chat", #"chat" | "completions"
            },
        })\
        .update()
    return