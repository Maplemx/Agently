from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace

class Status(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.status_runtime_ctx = RuntimeCtxNamespace("status", self.agent.agent_runtime_ctx)
        self.status_mapping_runtime_ctx = RuntimeCtxNamespace("status_mapping", self.agent.agent_runtime_ctx)
        self.status_storage = self.agent.global_storage.table("status")
        self.settings = RuntimeCtxNamespace("plugin_settings.agent_component.Status", self.agent.settings)
        self.global_status_namespace = None

        # Defer loading to avoid unnecessary actions in initialization
        if self.settings.get_trace_back("auto"):
            self.load()

    def set(self, key: str, value: str):
        self.status_runtime_ctx.set(key, value)
        return self.agent

    def use_global_status(self, namespace_name: str="default"):
        self.global_status_namespace = namespace_name
        return self.agent

    def append_mapping(self, status_key: str, status_value: str, alias_name: str, *args, **kwargs):
        self.status_mapping_runtime_ctx.append(
            f"{status_key}.{status_value}",
            {
                "alias_name": alias_name,
                "args": args,
                "kwargs": kwargs,
            }
        )
        return self.agent

    def save(self):
        status = self.status_runtime_ctx.get()
        self.status_storage.set(status).save()
        return self.agent

    def load(self):
        status = self.status_storage.get()
        self.status_runtime_ctx.update(status)
        return self.agent

    def _apply_mappings(self, mappings_dict, status_key, status_value):
        """Helper function to apply mappings to the agent."""
        if status_key in mappings_dict and status_value in mappings_dict[status_key]:
            for mapping in mappings_dict[status_key][status_value]:
                alias_func = getattr(self.agent, mapping["alias_name"], None)
                if alias_func:
                    alias_func(*mapping["args"], **mapping["kwargs"])

    def _prefix(self):
        agent_status = self.status_runtime_ctx.get()
        if not agent_status:
            return None

        # Load global mappings if the namespace is set
        global_mappings = {}
        if self.global_status_namespace:
            global_mappings = self.agent.global_storage.table(f"status_mapping.{self.global_status_namespace}").get() or {}

        agent_mappings = self.status_mapping_runtime_ctx.get() or {}

        for status_key, status_value in agent_status.items():
            self._apply_mappings(global_mappings, status_key, status_value)
            self._apply_mappings(agent_mappings, status_key, status_value)

        return None

    def export(self):
        return {
            "prefix": self._prefix,
            "suffix": None,
            "alias": {
                "set_status": {"func": self.set},
                "save_status": {"func": self.save},
                "load_status": {"func": self.load},
                "use_global_status": {"func": self.use_global_status},
                "append_status_mapping": {"func": self.append_mapping},
            },
        }

def export():
    return ("Status", Status)
