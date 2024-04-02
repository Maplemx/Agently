def create(workflow, chunk_id, chunk_info):
    @workflow.chunk(chunk_id=chunk_id, **chunk_info)
    def print_executor(inputs, storage):
        if len(inputs.keys()) == 1 and "input" in inputs:
            print(
                chunk_info["placeholder"] if "placeholder" in chunk_info else ">>>",
                inputs["input"]
            )
        else:
            print(
                chunk_info["placeholder"] if "placeholder" in chunk_info else ">>>",
                inputs
            )