def create(workflow, chunk_id, chunk_info):
    workflow.chunk(chunk_id=chunk_id, type="Start")(lambda:None)