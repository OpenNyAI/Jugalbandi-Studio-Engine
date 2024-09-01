import json
import re
import ast

# json_data should have the following structure
# {
#     "fsm_name": "CarDealerBot",
#     "config_variables" : [],
#     "variables": [],0
#     "dsl": []
# }


class CodeGen:

    def __init__(self, json_data):
        self.json_data = json_data

        self.fsm_class_name = self.json_data["fsm_name"]
        self.states = []
        self.transitions = []
        self.conditions = set()
        self.validation_methods = []
        self.on_enter_methods = []
        self.plugin_error_methods = []
        self.variables = {}
        for var in self.json_data["variables"]:
            self.variables[var["name"]] = var

    @classmethod
    def from_json_file(cls, json_file):
        with open(json_file) as f:
            json_data = json.load(f)
        return cls(json_data)

    def generate_pydantic_class(self, fsm_name, variables):
        var_map = {
            "str": "str",
            "string": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "list": "List",
            "List": "List",
            "dict": "Dict",
            "Dict": "Dict",
            "tuple": "Tuple",
            "Tuple": "Tuple",
            "set": "Set",
            "Set": "Set",
            "enum": "Enum",
            "Enum": "Enum",
            "literal": "Literal",
            "Literal": "Literal",
            "optional": "Optional",
        }
        class_def = f"class {fsm_name}Variables(BaseModel):\n"

        if len(variables) < 1:
            class_def += "    pass"

        for variable in variables:
            name = variable["name"]
            var_type = var_map[variable["type"]]
            validation = variable["validation"]

            # if f"{name} in" in validation:
            #     values = validation.split("[")[1].split("]")[0]
            #     class_def += f"    {name}: Optional[Literal[{values}]] = None\n"
            # else:
            #     class_def += f"    {name}: Optional[{var_type}] = None\n"
            default = None
            if var_type == "int":
                default = 0
            elif var_type == "float":
                default = 0.0
            elif var_type == "str":
                default = None
            elif var_type == "Dict":
                default = {}
            elif var_type == "List":
                default = []
            class_def += f"    {name}: Optional[{var_type}] = {default}\n"

            # if validation:
            #     class_def += f"    @validator('{name}')\n"
            #     class_def += f"    def validate_{name}(cls, v):\n"
            #     class_def += (
            #         f"        validation = lambda x: {validation.replace(name, 'x')}\n"
            #     )
            #     class_def += f"        if not validation(v):\n"
            #     class_def += (
            #         f"            raise ValueError('Invalid value for {name}')\n"
            #     )
            #     class_def += f"        return v\n"

        return class_def

    def generate_on_enter_plugin(self, task):
        state_name = task["name"]
        plugin = task["plugin"]
        if "message" in task:
            message = task["message"]
        else:
            message = None
        method_code = f"""
    def on_enter_{state_name}(self):
        self._on_enter_plugin(
            plugin="{plugin["name"]}",
            input_variables={plugin["inputs"]},
            output_variables={plugin["outputs"]},
            message="{message}"
        )
    """
        return method_code

    def generate_on_enter_condition(self, task):
        state_name = task["name"]
        method_code = f"""
    def on_enter_{state_name}(self):
        self._on_enter_empty_branching()
        """
        return method_code

    def generate_on_enter_display(self, task, name):
        message = task.get("message", "")
        options = task.get("options", None)
        menu_selector = task.get("menu_selector", None)
        menu_title = task.get("menu_title", None)

        # correct source of formatted strings
        msg_nobrace = message.replace("{{", "~~")[::-1].replace("}}", "~~")[::-1]
        brace_ranges = [m.span() for m in re.finditer(r"\{[^{}]+\}", msg_nobrace)]
        for pos_s, pos_e in brace_ranges[::-1]:
            if message[pos_s + 1:pos_e - 1] in self.variables:
                message = message[:pos_s + 1] + "self.variables." + message[pos_s+1:]

        if options:
            method_code = f"""
    def on_enter_{name}(self):
        self._on_enter_display(
            message=f"{message}",
            options={options},
            menu_selector={menu_selector},
            menu_title={menu_title},

        )
        """
        else:
            method_code = f"""
    def on_enter_{name}(self):
        self._on_enter_display(
            message=f"{message}",
        )
        """
        return method_code

    def generate_on_enter_input(self, task):
        input_state = f"{task['name']}_input"
        method_code = f"""
    def on_enter_{input_state}(self):
        self._on_enter_empty_input()
        """
        return method_code

    def generate_on_enter_logic(self, task, validation_expression, should_validate=True):
        logic_state = f"{task['name']}_logic"
        options = task.get("options", None)
        method_code = f"""
    def on_enter_{logic_state}(self):
        self._on_enter_input_logic(
            message="{task['message']}",
            write_var="{task['write_variable']}",
            options={options},
            validation="{validation_expression}",
            should_validate={should_validate}
        )
    """
        return method_code

    def generate_on_enter_assign(self, task, validation_expression):
        logic_state = f"{task['name']}"
        
        varlist = self.variables
        class VarTweaker(ast.NodeTransformer):
            def visit_Name(self, node):
                if node.id in varlist:
                    return ast.Name(**{**node.__dict__, 'id':"self.variables." + node.id})
                else:
                    return node
        
        correct_expr = ast.unparse(VarTweaker().visit(ast.parse(validation_expression)))

        # if correct expression has single = then it is assignment
        # else return the expression as it is
        if "=" in correct_expr:
            correct_expr = f"""
            {correct_expr}
            return self.variables.{str(task['write_variable'])}
"""
        else:
            correct_expr = f"""
            return {correct_expr}
"""

        method_code = f"""
    def on_enter_{logic_state}(self):
        variable_name = "{task['write_variable']}"
        expression = "{task['operation']}"
        def validation(*args):
            {correct_expr}
        self._on_enter_assign(variable_name, validation)
    """
        return method_code

    def generate_fsm_code(self):

        for task in self.json_data["dsl"]:
            # self.states Additions
            if task["task_type"] == "start":
                self.states.append("zero")
            elif task["task_type"] == "end":
                self.states.append(task["name"])
            elif task["task_type"] == "input":
                display_state = f"{task['name']}_display"
                input_state = f"{task['name']}_input"
                logic_state = f"{task['name']}_logic"

                self.states.extend([display_state, input_state, logic_state])

                method_name = f"is_valid_{task['name']}"
                validation = None

                if task["write_variable"] not in self.variables:
                    raise ValueError(
                        f"Variable {task['write_variable']} not found in variables"
                    )

                validation = self.variables[task["write_variable"]]["validation"]
                should_validate = task["should_validate"] if "should_validate" in task else True

                self.validation_methods.append(
                    (method_name, task["write_variable"], validation)
                )

                self.on_enter_methods.append(
                    {
                        "type": "display",
                        "state": task,
                        "name": display_state,
                    }
                )
                self.on_enter_methods.append({"type": "input", "state": task})
                self.on_enter_methods.append(
                    {
                        "type": "logic",
                        "state": task,
                        "validation_expression": validation,
                        "should_validate": should_validate
                    }
                )
            elif task["task_type"] == "print":
                display_state = task["name"]
                self.states.append(display_state)
                self.on_enter_methods.append(
                    {
                        "type": "display",
                        "state": task,
                        "name": display_state,
                    }
                )
            elif task["task_type"] == "condition":
                condition_state = task["name"]
                self.states.append(condition_state)
                self.on_enter_methods.append(
                    {
                        "type": "condition",
                        "state": task,
                    }
                )
                read_variables = task["read_variables"]
                state_transitions = task["conditions"]
                for idx, transition in enumerate(state_transitions):
                    for variable in read_variables:
                        if variable in transition["condition"]:
                            variable_name = variable
                    self.validation_methods.append(
                        (
                            f"is_valid_{condition_state}_{idx}",
                            variable_name,
                            transition["condition"],
                        )
                    )
            elif task["task_type"] == "plugin":
                plugin_state = task["name"]
                plugin_name = task["plugin"]["name"]
                self.states.append(plugin_state)
                state_transitions = task["transitions"]
                for idx, transition in enumerate(state_transitions):

                    self.plugin_error_methods.append(
                        {
                            "name": f"is_{plugin_state}_{transition['code']}",
                            "condition": transition["code"],
                            "plugin_name": plugin_name
                        }
                    )

                self.on_enter_methods.append(
                    {
                        "type": "plugin",
                        "state": task,
                    }
                )
            elif task["task_type"] == "operation":
                self.states.append(task["name"])
                expression = task["operation"]

                self.on_enter_methods.append(
                    {
                        "type": "operation",
                        "state": task,
                        "operation": expression,
                    }
                )

        for task in self.json_data["dsl"]:
            # self.transitions Additions
            if task["task_type"] == "start" or task["task_type"] == "end":
                goto = task["goto"]
                if goto is None:
                    continue
                if goto and goto not in self.states and goto != "end":
                    goto = f"{goto}_display"
                self.transitions.append(
                    {
                        "source": (
                            task["name"] if task["task_type"] == "end" else "zero"
                        ),
                        "dest": goto,
                        "trigger": "next",
                    }
                )
            elif task["task_type"] == "print":
                goto = task["goto"]
                if goto is None:
                    goto = "end"
                if goto and goto not in self.states and goto != "end":
                    goto = f"{goto}_display"

                self.transitions.append(
                    {
                        "source": task["name"],
                        "dest": goto,
                        "trigger": "next",
                    }
                )
            elif task["task_type"] == "input":
                display_state = f"{task['name']}_display"
                input_state = f"{task['name']}_input"
                logic_state = f"{task['name']}_logic"
                goto = task["goto"]
                error_goto = task["error_goto"]

                self.transitions.extend(
                    [
                        {
                            "source": display_state,
                            "dest": input_state,
                            "trigger": "next",
                        },
                        {
                            "source": input_state,
                            "dest": logic_state,
                            "trigger": "next"
                        }
                    ]
                )
                if goto is None:
                    goto = "end"
                if goto and goto not in self.states and goto != "end":
                    goto = f"{goto}_display"

                if error_goto is None:
                    error_goto = "end"
                if error_goto and error_goto not in self.states and error_goto != "end":
                    error_goto = f"{error_goto}_display"

                self.transitions.extend(
                    [
                        {
                            "source": logic_state,
                            "dest": goto,
                            "trigger": "next",
                            "conditions": f"is_valid_{task['name']}",
                        },
                        {"source": logic_state, "dest": error_goto, "trigger": "next"},
                    ]
                )
            elif task["task_type"] == "condition":
                condition_state = task["name"]
                state_transitions = task["conditions"]
                for idx, transition in enumerate(state_transitions):
                    if transition["goto"] is None:
                        transition["goto"] = "end"
                    if transition["goto"] and transition["goto"] not in self.states:
                        transition["goto"] = f"{transition['goto']}_display"
                    self.transitions.append(
                        {
                            "source": condition_state,
                            "dest": transition["goto"],
                            "trigger": "next",
                            "conditions": f"is_valid_{condition_state}_{idx}",
                        }
                    )
            elif task["task_type"] == "plugin":
                plugin_state = task["name"]
                state_transitions = task["transitions"]
                for idx, transition in enumerate(state_transitions):
                    self.transitions.append(
                        {
                            "source": plugin_state,
                            "dest": transition["goto"],
                            "trigger": "next",
                            "conditions": f"is_{plugin_state}_{transition['code']}",
                        }
                    )
            elif task["task_type"] == "operation":
                goto = task["goto"]
                if goto is None:
                    goto = "end"
                if goto and goto not in self.states and goto != "end":
                    goto = f"{goto}_display"

                self.transitions.append(
                    {
                        "source": task["name"],
                        "dest": goto,
                        "trigger": "next",
                    }
                )

        self.code = f"""
from typing import Dict, Any, Type, List, Tuple, Set, Optional, Literal
from pydantic import BaseModel, Field
from jb_manager_bot import AbstractFSM
from jb_manager_bot.data_models import FSMOutput
import re
"""
        plugin_names = set()
        for task in self.json_data["dsl"]:
            if task["task_type"] == "plugin":
                plugin_names.add(task["plugin"]["name"])
                self.code += f"""from jb_{task["plugin"]["name"]} import {task["plugin"]["name"]}, {task["plugin"]["name"]}ReturnStatus
"""
        pydantic_code = self.generate_pydantic_class(
            self.fsm_class_name, self.json_data["variables"]
        )
        pydantic_code = "\n".join(["" + l for l in pydantic_code.split("\n")])

        plugin_init_code = ""
        for plugin in plugin_names:
            plugin_init_code += f"""
            "{plugin}": {plugin}(send_message=send_message),
        """
        self.code += f"""
{pydantic_code}

class {self.fsm_class_name}(AbstractFSM):
    states = {self.states}
    transitions = {self.transitions}
    conditions = {set(self.conditions)}
    output_variables = set()
    variable_names = {self.fsm_class_name}Variables


    def __init__(self, send_message: callable, credentials: Dict[str, Any] = None):
        if credentials is None:
            credentials = {{}}

        self.credentials = {{}}

        for variable in {json.dumps(self.json_data["config_vars"])}:
            if not credentials.get(variable["name"]):
                raise ValueError(f"Missing credential: {{variable['name']}}")
            self.credentials[variable["name"]] = credentials.get(variable["name"])
        self.plugins: Dict[str, AbstractFSM] = {{
            {plugin_init_code}
        }}
        self.variables = self.variable_names()
        super().__init__(send_message=send_message)
    """
        # code+="""
        # def on_enter_select_language(self):
        #     self.status = Status.WAIT_FOR_ME
        #         self.send_message(
        #             FSMOutput(
        #                 message_data=MessageData(
        #                     body="Please select your preferred language.\nबंधु से संपर्क करने के लिए धन्यवाद!\nकृपया अपनी भाषा चुनें।"
        #                 ),
        #                 type=MessageType.TEXT,
        #                 dialog="language",
        #                 dest="channel",
        #             )
        #         )
        #         self.status = Status.WAIT_FOR_USER_INPUT

        # """

        for method in self.on_enter_methods:
            if method["type"] == "display":
                self.code += self.generate_on_enter_display(
                    method["state"], method["name"]
                )
            elif method["type"] == "input":
                self.code += self.generate_on_enter_input(method["state"])
            elif method["type"] == "logic":
                self.code += self.generate_on_enter_logic(
                    method["state"], method["validation_expression"], method.get("should_validate", True)
                )
            elif method["type"] == "condition":
                self.code += self.generate_on_enter_condition(method["state"])
            elif method["type"] == "plugin":
                self.code += self.generate_on_enter_plugin(method["state"])
            elif method["type"] == "operation":
                self.code += self.generate_on_enter_assign(
                    method["state"], method["operation"]
                )

        for method in self.validation_methods:
            self.code += f"""
    def {method[0]}(self):
        variable_name = "{method[1]}"
        validation = lambda x: {method[2].replace(method[1], "x")}
        return self._validate_method(variable_name, validation)
    """

        for method in self.plugin_error_methods:
            self.code += f"""
    def {method["name"]}(self):
        return self._plugin_error_code_validation({method["plugin_name"]}ReturnStatus.{method["condition"]})
        """
        return self.code

