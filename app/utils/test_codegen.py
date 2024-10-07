from .codegen import CodeGen


class TestCodegen(CodeGen):

    def generate_plugin_display(self, task):
        state_name = task["name"]
        plugin = task["plugin"]
        plugin_name = plugin["name"]
        output_variables = plugin["outputs"]
        output_variable_keys = list(output_variables.keys())
        output_error_codes = [transition["code"] for transition in task["transitions"]]

        method_code = f"""
    def on_enter_{state_name}_display(self):
        self.status = Status.WAIT_FOR_ME
        self.send_message(
            Plugin(
                name="{plugin_name}",
                output_variables={output_variable_keys},
                error_codes={output_error_codes},
            ),
        )
        self.status = Status.MOVE_FORWARD
    """
        return method_code

    def generate_plugin_input_processing(self, task):
        state_name = task["name"]
        plugin = task["plugin"]
        output_variables = plugin["outputs"]

        method_code = f"""
    def on_enter_{state_name}_logic(self):
        self.status = Status.WAIT_FOR_ME
        user_input = json.loads(self.current_input)
        self.temp_variables["error_code"] = user_input["plugin_status"]

        plugin_output = user_input["plugin_output"]
        output_variables = {output_variables}
        for key, value in output_variables.items():
            setattr(self.variables, value, plugin_output[key])
        
        self.status = Status.MOVE_FORWARD
    """
        return method_code

    def generate_on_enter_plugin(self, task):
        method_code = ""
        method_code += self.generate_plugin_display(task)
        method_code += self.generate_on_enter_input(task)
        method_code += self.generate_plugin_input_processing(task)
        return method_code

    def generate_plugin_imports(self):
        self.code += """
from jb_manager_bot.data_models import Status
"""

    def get_plugin_init_code(self):
        return ""

    def generate_plugin_state(self, task):
        display_state = f"{task['name']}_display"
        input_state = f"{task['name']}_input"
        logic_state = f"{task['name']}_logic"

        self.states.extend([display_state, input_state, logic_state])
        self.on_enter_methods.append(
            {
                "type": "plugin",
                "state": task,
            }
        )

    def generate_plugin_error_methods(self):
        for method in self.plugin_error_methods:
            self.code += f"""
    def {method["name"]}(self):
        return self._plugin_error_code_validation("{method["condition"]}")
"""

    def generate_class_scaffold(self):
        self.code += f"""
class Plugin(BaseModel):
    name: str
    output_variables: List[str]
    error_codes: List[str]

"""
        super().generate_class_scaffold()

    def generate_plugin_transition(self, task):
        display_state = f"{task['name']}_display"
        input_state = f"{task['name']}_input"
        logic_state = f"{task['name']}_logic"
        plugin_state = task["name"]
        state_transitions = task["transitions"]
        self.transitions.append(
            {
                "source": display_state,
                "dest": input_state,
                "trigger": "next",
            }
        )
        self.transitions.append(
            {
                "source": input_state,
                "dest": logic_state,
                "trigger": "next",
            }
        )
        plugin_name = task["plugin"]["name"]
        for idx, transition in enumerate(state_transitions):
            self.plugin_error_methods.append(
                {
                    "name": f"is_{plugin_state}_{transition['code']}",
                    "condition": transition["code"],
                    "plugin_name": plugin_name,
                }
            )
            self.transitions.append(
                {
                    "source": logic_state,
                    "dest": transition["goto"],
                    "trigger": "next",
                    "conditions": f"is_{plugin_state}_{transition['code']}",
                }
            )