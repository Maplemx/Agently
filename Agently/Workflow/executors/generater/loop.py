
import inspect
from ...lib.Store import Store
from ...lib.constants import DEFAULT_INPUT_HANDLE_VALUE

def use_loop_executor(sub_workflow):
    async def loop_executor(inputs, store: Store, **sys_info):
        # Run Loop
        input_val = inputs.get(DEFAULT_INPUT_HANDLE_VALUE)
        all_result = []
        if isinstance(input_val, list):
            for val in input_val:
                all_result.append(await loop_unit_core(unit_val=val, store=store))
        elif isinstance(input_val, dict):
            for key, value in input_val.items():
                all_result.append(await loop_unit_core(unit_val={
                    "key": key,
                    "value": value
                }, store=store))
        elif isinstance(input_val, int):
            for i in range(input_val):
                all_result.append(await loop_unit_core(unit_val=i, store=store))
        # Old Version Compatible
        if sub_workflow.settings.get("compatible_version") and sub_workflow.settings.get("compatible_version") <= 3315:
            return all_result
        else:
            # Regroup
            final_result = {}
            for one_result in all_result:
                for handle, result in one_result.items():
                    if handle not in final_result:
                        final_result.update({ handle: [] })
                    final_result[handle].append(result)
            return final_result

    async def loop_unit_core(unit_val, store):
        if inspect.iscoroutinefunction(sub_workflow):
            return await sub_workflow(unit_val, store)
        elif inspect.isfunction(sub_workflow):
            return sub_workflow(unit_val, store)
        else:
            return await sub_workflow.start_async(unit_val)
    
    return loop_executor
