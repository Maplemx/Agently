class EnvBox(object):
    def __init__(self, agently):
        self.env_data = {
            # 目标
            "target": "",
            # 整体计划
            "overall_plan": "",
            # 结果数据
            "data": {},
            # 可调用的方法
            "func": {}
            
        }
        self.overwatcher = None
        self.agents = {}
        self.agently = agently
        self.options = {
            "show_process": False,
        }

    def set_overwatcher(self, overwatcher):
        self.overwatcher = overwatcher
        return self
    
    def set_plan(self, plan):
        self.env_data["overall_plan"] = plan
        return self

    def set_target(self, target):
        self.env_data["target"] = target
        return self

    def set_data(self, key, value):
        self.env_data["data"].update({ key: value })
        return self

    def get_data(self, key, value):
        return self.env_data["data"]["key"] if "key" in self.env_data["data"] else None

    def register_func(self, func_name, desc, parameter_requirement, func):
        self.env_data["func"].update({
            func_name:
                {
                    "desc": desc,
                    "parameter_requirement": parameter_requirement,
                    "func": func
                }
        })
        return self

    def register_agent(self, agent_name, agent_purpose, agent):
        self.agents.update({
            agent_name:
                {
                    "purpose":agent_purpose,
                    "agent": agent
                }
        })
        return self

    def set_options(self, key, value):
        self.options.update({ key: value })
        return self

    def set_main_func(self, main_func):
        self.__main_func = main_func
        return self

    def __main_func(self):
        is_solved = False
        achievement = []
        final_reply = None

        # 整理可用的 agent 信息
        agents_info = []
        for agent_name in self.agents.keys():
            agents_info.append({
                "name": agent_name,
                "purpose": self.agents[agent_name]["purpose"]
            })
        # 整理可用的 function
        func_info = []
        for func_name in self.env_data["func"].keys():
            func_info.append({
                "name": func_name,
                "desc": self.env_data["func"][func_name]["desc"],
                "parameter_requirement": self.env_data["func"][func_name]["parameter_requirement"]
            })
        overwatcher = self.overwatcher
        # 全局观察者设定
        overwatcher\
            .use_role(True)\
            .set_role("Relevant Data", self.env_data["data"])\
            .set_role("Agent You Can Call", agents_info)\
            .set_role("Func You Can Call", func_info)
        
        # 根据目标、agent角色、可调用的方法，输出整体的执行计划
        if self.env_data["overall_plan"] == "":
            overall_planner_session = overwatcher.create_session()
            overall_plan = overall_planner_session\
                    .input({
                        "achievement": achievement,
                        "target": self.env_data["target"]
                    })\
                    .output({
                        "overall_plan": ("String", "Based on the {{target}} and the {{Agent You Can Call}} and the {{Func You Can Call}}, establish your detailed global plan（Using \"ReAct\" mode）, requiring a clear description for each step indicating which role should perform what task, and strive to efficiently accomplish the target."),
                    })\
                    .start()
            if self.options["show_process"]:
                print('[Overall plan]\n', overall_plan)
            self.env_data['overall_plan'] = overall_plan
        
        next_task = "Prepare to start."

        while not is_solved:
            next_move_judgement_session = overwatcher.create_session()

            next_move_judgement = next_move_judgement_session\
                .input({
                    "achievement": achievement,
                    "target": self.env_data["target"],
                    "current_task": next_task
                })\
                .output({
                    "next_task": ("String", "Describe the next child task according {{Overall plan}} and {{current_task}}."),
                    "next_move_type": ("call | text | reply", "Judge type of your next move:'call' to call agent or func to help; 'text' to output your text anwser to {{next_task}}; 'reply' to generate final reply to {{target}} according {{Overall plan}} and {{achievement}}"),
                    "call": {
                        "type": ("agent | func | null", "output 'agent' or 'func' you want to call if {{next_move_type}} is 'call', else output 'null'"),
                        "name": ("String", "name of agent or func in {{Agent You Can Call}} or {{Func You Can Call}}"),
                        "parameter": ("String | dict according to {{parameter_requirement}}", "input string you want to tell the agent to do if {{call.type}} is 'agent'; parameters dict the func required if {{call.type}} is 'func'.")
                    },
                    "text": {
                        "type": ("text | reply", "'text' for anwser to {{next_task}} that will storage to {{achievement}}; 'reply' for final reply to {{target}}."),
                        "content": ("String",)
                    },
                })\
                .start()

            if self.options["show_process"]:
                print('[Next Move Judgement]\n', next_move_judgement)
            
            next_task = next_move_judgement["next_task"]

            # 一、处理调用逻辑
            if next_move_judgement["next_move_type"] == "call":
                # 处理 agent 调用
                if next_move_judgement["call"]["type"] == "agent":
                    agent_session = self.agents[next_move_judgement["call"]["name"]]["agent"].create_session()
                    agent_result = agent_session\
                        .input({
                            "achievement": achievement,
                            "target": next_move_judgement["call"]["parameter"],
                        })\
                        .output({
                            "output": ("String", "Your work output to {{target}}.")
                        })\
                        .start()
                    achievement.append(f"Agent [{ next_move_judgement['call']['name'] }]: { agent_result['output'] }")
                    if self.options["show_process"]:
                        print('[Achievement]\n', agent_result)
                # 处理 function 调用
                if next_move_judgement["call"]["type"] == "func":
                    func_result = self.env_data["func"][next_move_judgement["call"]["name"]]["func"](next_move_judgement["call"]["parameter"])
                    achievement.append(f"Func [{ next_move_judgement['call']['name'] }]: { func_result }")
                    if self.options["show_process"]:
                        print('[Achievement]\n', func_result)
            # 二、处理文本内容返回
            if next_move_judgement["next_move_type"] == "text":
                achievement.append(f"Res: { next_move_judgement['text']['content'] }")
                if self.options["show_process"]:
                    print('[Achievement]\n', next_move_judgement['text']['content'])
            # 三、处理最终结果
            if next_move_judgement["next_move_type"] == "reply":
                achievement.append(f"Final: { next_move_judgement['text']['content'] }")
                if self.options["show_process"]:
                    print('[Achievement]\n', next_move_judgement['text']['content'])
                final_reply = next_move_judgement["text"]["content"]
                is_solved = True

        return {
            "process_achievement": achievement,
            "final_reply": final_reply
        }

    def start(self):
        return self.__main_func()