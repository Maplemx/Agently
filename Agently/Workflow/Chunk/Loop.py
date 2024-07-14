import inspect
from typing import TYPE_CHECKING
from ..executors.generater.loop import use_loop_executor
from ..lib.constants import EXECUTOR_TYPE_LOOP
from .helper import exposed_interface

if TYPE_CHECKING:
    from . import SchemaChunk

class LoopAbility:
    """提供Loop API"""

    def __init__(self) -> None:
        self.shared_ns['loop'] = {}
        super().__init__()

    @exposed_interface(type='connect_command')
    def loop_with(self, sub_workflow) -> 'SchemaChunk':
        """遍历逐项处理，支持传入子 workflow/处理方法 作为处理逻辑"""
        is_function = inspect.isfunction(sub_workflow) or inspect.iscoroutinefunction(sub_workflow)
        # 这里是新的 chunk，需要走 Schema 的 create 方法挂载
        loop_chunk = self.create_rel_chunk(
            type=EXECUTOR_TYPE_LOOP,
            title="Loop",
            executor=use_loop_executor(sub_workflow),
            extra_info={
                # loop 的相关信息
                "loop_info": {
                    "type": 'function' if is_function else 'workflow',
                    "detail": sub_workflow.__name__ if is_function else sub_workflow.schema.compile()
                }
            }
        )
        return self._raw_connect_to(loop_chunk)
