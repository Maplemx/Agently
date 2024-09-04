
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
        if inspect.isfunction(sub_workflow) or inspect.iscoroutinefunction(sub_workflow):
            return all_result
        elif hasattr(sub_workflow, "settings") and sub_workflow.settings.get("compatible_version") and sub_workflow.settings.get("compatible_version") <= 3316:
            return all_result
        else:
            # Regroup
            final_result = {}
            i = 0
            for one_result in all_result:
                if one_result:
                    used_handle_pool = []
                    for handle, result in one_result.items():
                        if handle not in final_result:
                            final_result.update({ handle: [None] * i })
                        final_result[handle].append(result)
                        used_handle_pool.append(handle)
                    for final_result_handle in final_result.keys():
                        if final_result_handle not in used_handle_pool:
                            final_result[final_result_handle].append(None)
                else:
                    if "default" not in final_result:
                        final_result.update({ "default": [None] * i })
                    final_result["default"].append(None)
                    for final_result_handle in final_result.keys():
                        if final_result_handle != "default":
                            final_result[final_result_handle].append(None)
                i += 1
            return final_result

    async def loop_unit_core(unit_val, store={}):
        if inspect.iscoroutinefunction(sub_workflow):
            return await sub_workflow(unit_val, store)
        elif inspect.isfunction(sub_workflow):
            return sub_workflow(unit_val, store)
        else:
            return await sub_workflow.start_async(unit_val, storage=store.get_all() if store else {})
    
    return loop_executor
