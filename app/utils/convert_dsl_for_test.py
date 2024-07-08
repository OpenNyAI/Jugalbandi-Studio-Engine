import json
import sys

def create_var(name, vtype):
    var_info = {}
    var_info["name"] = name
    var_info["type"] = vtype
    var_info["validation"] = f"isinstance({name}, {vtype})"
    return var_info

def make_str_format_friendly(msg:str):
    msg = msg.replace('{', '{{')
    msg = msg.replace('}', '}}')
    msg = msg.replace('\n', '\\n')
    msg = msg.replace('"', '\\"')
    return msg

def make_message_for_variable_list(var_type, var_list):
    all_cvar_names = ['"' + x + '"' for x in var_list]
    cv_names = ', '.join(all_cvar_names)
    cvar_config = f'{{"type": "form","vars": [{cv_names}]}}'
    msg = cvar_config + '\xa1' + f"Enter the values for the following {var_type}:\n\n" + '\n\n'.join(all_cvar_names)
    return msg

def convert_dsl(dsl: str) -> str:
    old_dsl = json.loads(dsl)
    new_dsl = {}

    new_dsl["fsm_name"] = old_dsl["fsm_name"]
    new_dsl["config_vars"] = old_dsl["config_vars"]
    new_dsl["variables"] = old_dsl["variables"]
    new_dsl["dsl"] = old_dsl["dsl"]

    # fix first task as zero
    if new_dsl['dsl'][0]['name'] != 'zero':
        inst = {}
        inst['task_type'] = 'start'
        inst['name'] = 'zero'
        inst['goto'] = new_dsl['dsl'][0]['name']

        if new_dsl['dsl'][0]['task_type'] == 'start':
            new_dsl['dsl'][0]['task_type'] = 'print'
            new_dsl['dsl'][0]['message'] = ''

        new_dsl['dsl'].insert(0, inst)

    all_var_list = set([x["name"] for x in new_dsl["variables"]])

    # find and replace configs as text inputs
    if len(new_dsl["config_vars"]) > 0:
        new_dsl["dsl"][0]["name"] += "_alt"
        start_name = new_dsl["dsl"][0]["name"]

        new_input_tasks = []
        new_vars_list = []

        # special case
        if new_dsl["dsl"][0]["task_type"] == "start":
            new_dsl["dsl"][0]["task_type"] = "print"

            if "message" not in new_dsl["dsl"][0]:
                new_dsl["dsl"][0]["message"] = ""

        # start by taking secrets
        first_config_task = {}
        first_config_task["task_type"] = "print"
        first_config_task["name"] = "zero"
        first_config_task["message"] = "Welcome, to start the program, please provide the following key/secret values."
        first_config_task["goto"] = new_dsl["config_vars"][0]["name"] + "_cnf_t"
        new_input_tasks.append(first_config_task)

        for i, cfg in enumerate(new_dsl["config_vars"]):
            inp_task = {}
            iname = cfg['name']
            idesc = cfg['description']
            inp_task["task_type"] = "input"
            inp_task["name"] = iname + "_cnf_t"

            # custom message for first input
            if i == 0:
                dsl_msg = make_message_for_variable_list("configuration variables", [x["name"] for x in new_dsl["config_vars"]])

                # make this object codegen compliant
                dsl_msg = make_str_format_friendly(dsl_msg)

                inp_task["message"] =  dsl_msg
            else:
                inp_task["message"] = ""

            inp_task["write_variable"] = iname
            inp_task["datatype"] = "str"

            next_task = start_name
            if i < len(new_dsl["config_vars"]) - 1:
                next_task = new_dsl["config_vars"][i + 1]["name"] + "_cnf_t"

            inp_task["goto"] = next_task
            inp_task["error_goto"] = next_task
            inp_task["should_validate"] = False

            new_input_tasks.append(inp_task)

            var_info = create_var(iname, "str")
            new_vars_list.append(var_info)

        # add configs as variables
        if not new_dsl["variables"]:
            new_dsl["variables"] = []

        for v in new_vars_list:
            new_dsl["variables"].append(v)

        # add the variables inputs
        for i, t in enumerate(new_input_tasks):
            new_dsl["dsl"].insert(i, t)

        # remove the configs
        new_dsl["config_vars"] = []

    # find and replace plugins as text inputs
    new_step_insertion = []
    for i in range(len(new_dsl["dsl"]) -1, -1, -1):
        task = new_dsl["dsl"][i]
        if task["task_type"] == "plugin":
            name = task["name"]
            output_vars = task["write_variables"]
            if not output_vars:
                output_vars = []
            output_vars.insert(0, name + "_code")

            transitions = task["transitions"]

            substitute_task_list = []

            # output conditions
            api_result_branch = {}
            api_result_branch["task_type"] = "condition"
            api_result_branch["name"] = name + "_condition_t"
            api_result_branch["read_variables"] = [name + "_code",]

            t_choices = []

            jump_list = []
            for t in transitions:
                # fix codes
                strcode = str(t["code"])

                jump = {}
                t_choices.append(strcode)
                jump["condition"] = name + "_code == '" + strcode + "'"
                jump["goto"] = t["goto"]
                jump["description"] = t["description"]
                jump_list.append(jump)

            api_result_branch["conditions"] = jump_list

            # simulate input tasks
            plugin_name = task["plugin"]["name"]
            plugin_inputs = ""

            for k, v in task["plugin"]["inputs"].items():
                if v in all_var_list:
                    plugin_inputs += f"{k}: {{{v}}}\\n"
                else:
                    plugin_inputs += f"{k}: {v}\\n"

            plugin_outputs = "api return code\\n" +  "\\n".join(task["plugin"]["outputs"].keys())
            plugin_desc = task["description"]

            common_desc = f"##plugin {plugin_name}##\\n\\nPlease enter simulated output of the plugin :\\n\\nThe plugin does the following : {plugin_desc}\\n\\nThe plugin inputs are the following : {plugin_inputs}\\nProvide values for the following variables :\\n{plugin_outputs}"

            first_output_task = {}
            first_output_task["task_type"] = "print"
            first_output_task["name"] = name
            first_output_task["message"] = common_desc
            first_output_task["goto"] = name + "_code_inp_t"
            substitute_task_list.append(first_output_task)

            print('###############')
            print(output_vars)

            for j, v in enumerate(output_vars):
                otask = {}
                otask["task_type"] = "input"
                otask["name"] = v + "_inp_t"
                otask["should_validate"] = False

                if j == 0:
                    otask["message"] = f"Enter value for plugin api call HTTP code"
                elif j == 1:
                    if len(output_vars) > 2:
                        # ask for all variables
                        pg_msg = make_message_for_variable_list("plugin outputs", output_vars[1:])
                        otask["message"] = make_str_format_friendly(pg_msg)
                    else:
                        otask["message"] = f"Enter value for {v}"
                else:
                    otask["message"] = ""

                otask["write_variable"] = v
                otask["datatype"] = "str"

                if j == 0 and len(t_choices) > 0:
                    otask["options"] = t_choices

                if v not in all_var_list:
                    var_info = create_var(v, otask["datatype"])
                    new_dsl["variables"].append(var_info)

                next_task = api_result_branch["name"]
                if j < len(output_vars) - 1:
                    next_task = output_vars[j + 1] + "_inp_t"

                otask["goto"] = next_task
                otask["error_goto"] = otask["name"]
                substitute_task_list.append(otask)

            substitute_task_list.append(api_result_branch)
            new_step_insertion.append((i, substitute_task_list))

    if len(new_step_insertion) > 0:
        for i in range(len(new_step_insertion) -1, -1, -1):
            pos, nsteps = new_step_insertion[i]
            new_dsl["dsl"].pop(pos)

            for j in range(len(nsteps)):
                new_dsl["dsl"].insert(pos + j, nsteps[j])

    # for input fields with options, add json to select drop down
    for step in new_dsl["dsl"]:
        if step["task_type"] == "input":
            if "options" in step and step["options"] is not None and len(step["options"]) > 0:
                if '\xa1' not in step["message"]:
                    json_ops = {}
                    json_ops["type"] = "dropdown"
                    json_ops["options"] = step["options"]
                    opt_str = make_str_format_friendly(json.dumps(json_ops))
                    step["message"] = opt_str + '\xa1' + step["message"]

    return json.dumps(new_dsl, indent=4)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            print(convert_dsl(f.read()))
