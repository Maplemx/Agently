import uuid
from typing import TYPE_CHECKING
from ..lib.constants import EXECUTOR_TYPE_CONDITION
from .helper import exposed_interface

if TYPE_CHECKING:
    from . import SchemaChunk

class ConditionAbility:
    """提供条件判断 API"""

    def __init__(self, **chunk_desc):
        self.shared_chain_ns['condition_ns'] = {
            'condition_chunk_path': chunk_desc.get('condition_chunk_path', [])
        }
        super().__init__()

    @exposed_interface(type='connect_command')
    def if_condition(self, condition: callable = None) -> 'SchemaChunk':
        """条件判断"""
        condition_signal_id = str(uuid.uuid4())
        # 创建新的 condition chunk，需要走 Schema 的 create 方法挂载
        condition_chunk = self.create_rel_chunk(
            type=EXECUTOR_TYPE_CONDITION,
            title="Condition",
            extra_info={
                # condition 的相关信息
                "condition_info": {
                    # 常规条件
                    "conditions": [{
                        # 命中时的结果符号
                        "condition_signal": condition_signal_id,
                        "condition": condition
                    }],
                    "else_condition": {
                        # 命中时的结果符号
                        "condition_signal": str(uuid.uuid4())
                    }
                }
            }
        )
        new_path_item = {
            'root': self,
            'condition': condition_chunk,
            # 关联的句柄(本质也是Chunk实例)
            'handles': []
        }
        # 以 condition_chunk 为起点，追加上条件路径信息（下游条件逻辑都可基于此判断处理）
        condition_chunk.shared_chain_ns['condition_ns']['condition_chunk_path'].append(new_path_item)
        # 把上游chunk连接到主判断节点（仅 if 时操作一次即可，后续皆为连接到condition chunk）
        connected_chunk_handle = self._raw_connect_to(condition_chunk)
        # 新连接的第一个 chunk，也需要补充本次的条件路径
        connected_chunk_handle.shared_chain_ns['condition_ns']['condition_chunk_path'].append(new_path_item)
        # 设置条件参数和辅助信息
        connected_chunk_handle.set_connect_condition(
            condition=lambda runtime_signal, storage: runtime_signal == condition_signal_id,
            condition_detail={
                # condition id
                "id": f"cid-{str(uuid.uuid4())}",
                "type": "if"
            }
        )
        return connected_chunk_handle

    @exposed_interface(type='connect_command')
    def elif_condition(self, condition: callable = None) -> 'SchemaChunk':
        """elif 条件判断"""
        # Step1. 从当前 chunk 中，读取所属的条件 chunk id 信息
        condition_path = self.shared_chain_ns['condition_ns']['condition_chunk_path']
        condition_path_item = condition_path[-1] if condition_path else None
        if not condition_path_item:
            raise ValueError(
                f"The `elif_condition` method must be called after the `if_condition` method.")

        condition_chunk: 'SchemaChunk' = condition_path_item.get('condition')
        # Step2. 基于 condition_chunk 做进一步的连接和更新操作
        # 2.1 生成 elif_fn
        condition_signal_id = str(uuid.uuid4())
        condition_info = (condition_chunk.chunk.get(
            'extra_info') or {}).get('condition_info') or {}
        # 追加条件信号
        condition_info.get('conditions', []).append({
            # 命中时的结果符号
            "condition_signal": condition_signal_id,
            "condition": condition
        })

        # 2.2 进行条件连接
        # 设置条件链接信息
        condition_chunk.set_connect_condition(
            condition=lambda runtime_signal, storage: runtime_signal == condition_signal_id,
            condition_detail={
                "id": (condition_chunk.chunk.get('connect_condition_detail') or {}).get('id') or f"cid-{str(uuid.uuid4())}",
                "type": "elif"
            }
        )
        shadow_root_chunk = condition_chunk.copy_shadow_chunk()
        # 将 elif 的上一个端点存入 handles 点中（后续结束时要统一处理）
        shadow_root_chunk.save_condition_end_handles(self)
        return shadow_root_chunk

    @exposed_interface(type='connect_command')
    def else_condition(self) -> 'SchemaChunk':
        """
        按当前条件的反条件连接（特别注意，else_condition 作用的 chunk 为往前追溯的最近一个 if_condition 作用的 chunk，两是同一个，成套存在的）
        """
        # Step1. 从当前 chunk 中，读取所属的条件 chunk id 信息
        condition_path = self.shared_chain_ns['condition_ns']['condition_chunk_path']
        condition_path_item = condition_path[-1] if condition_path else None
        if not condition_path_item:
            raise ValueError(
                f"The `else_condition` method must be called after the `if_condition` method.")

        condition_chunk: 'SchemaChunk' = condition_path_item.get('condition')
        # Step2. 基于 condition_chunk 做进一步的连接和更新操作
        # 2.1 生成 else_fn
        condition_info = (condition_chunk.chunk.get(
            'extra_info') or {}).get('condition_info') or {}
        else_signal = (condition_info.get('else_condition') or {}).get(
            'condition_signal') or str(uuid.uuid4())

        # 2.2 进行条件连接
        # 在 shadow_root_chunk 上操作，支撑参数剔除当前所在条件 chunk 后继续保留
        shadow_root_chunk = condition_chunk.copy_shadow_chunk()
        # 设置条件链接信息
        shadow_root_chunk.set_connect_condition(
            condition=lambda runtime_signal, storage: runtime_signal == else_signal,
            condition_detail={
                "id": (condition_chunk.chunk.get('connect_condition_detail') or {}).get('id') or f"cid-{str(uuid.uuid4())}",
                "type": "else"
            }
        )
        # 将 else 的上一个端点存入 handles 点中（后续结束时要统一处理）
        shadow_root_chunk.save_condition_end_handles(self)
        return shadow_root_chunk

    @exposed_interface(type='connect_command')
    def end_condition(self) -> 'SchemaChunk':
        """终止当前所在的if，回退到当次 if 前的 chunk"""
        # Step1. 从当前 chunk 中，读取所属的条件 chunk id 信息
        condition_path = self.shared_chain_ns['condition_ns']['condition_chunk_path']
        condition_path_item = condition_path[-1] if condition_path else None
        if not condition_path_item:
            raise ValueError(
                f"The `end_condition` method must be called after the `if_condition` method.")
        # Step2. 将 end 的上一个端点存入 handles 点中（后续结束时要统一处理）
        shadow_chunk = self.copy_shadow_chunk()
        shadow_chunk.save_condition_end_handles(self)
        # Step3. 汇总所有 handles，统一连接到下一个节点（未来）
        def future_commands(chunk: 'SchemaChunk', type, name, res):
            # 针对 command 类型，执行future
            if type == 'connect_command':
                condition_end_handles = chunk.get_condition_end_handles()
                # 将本次 condition的所有末级端点批量连接到 end_condition 之后的端点上
                if condition_end_handles:
                    for end_handle in condition_end_handles:
                        # 跳过自身，只处理其它端点
                        if end_handle.chunk['id'] == shadow_chunk.chunk['id']:
                            continue
                        # 调用其它端点的处理逻辑
                        end_handle._raw_connect_to(res.copy_shadow_chunk())

            # 针对其它类型报错处理
            else:
                raise TypeError("After end_condition, the method cannot be called directly.")

        shadow_chunk._post_command_interceptors.append(future_commands)
        return shadow_chunk

    def set_connect_condition(self, condition: callable = None, condition_detail: dict = None):
        """设置连接的条件"""
        self.chunk['connect_condition'] = condition
        self.chunk['connect_condition_detail'] = condition_detail
        return self
    
    def get_condition_end_handles(self):
        """获取当前条件的结束的句柄 chunk（注意，此句柄是挂载在 condition_chunk 上的）"""
        # 找到 condtion_chunk 的handles
        condition_path = self.shared_chain_ns['condition_ns']['condition_chunk_path']
        if not condition_path:
            return []
        condtion_chunk = self.shared_chain_ns['condition_ns']['condition_chunk_path'][-1]['condition']
        current_handles = condtion_chunk.shared_chain_ns[
            'condition_ns']['condition_chunk_path'][-1]['handles']
        return current_handles

    def save_condition_end_handles(self, handle_chunk: 'SchemaChunk'):
        """保存 condition 的各连接端点句柄"""
        # 找到 condtion_chunk 的handles
        condtion_chunk = self.shared_chain_ns['condition_ns']['condition_chunk_path'][-1]['condition']
        current_handles = condtion_chunk.shared_chain_ns['condition_ns']['condition_chunk_path'][-1]['handles']
        # 如果已存在，则忽略
        for handle in current_handles:
            if handle.chunk['id'] == handle_chunk.chunk['id']:
                return self
        current_handles.append(handle_chunk)
        return self
