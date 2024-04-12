def create(workflow, chunk_id, chunk_info):
    @workflow.chunk(chunk_id=chunk_id, **chunk_info)
    def user_input_executor(inputs, storage):
        input_str = input(
            chunk_info["placeholder"] if "placeholder" in chunk_info else "[User]:",
        )
        return input_str