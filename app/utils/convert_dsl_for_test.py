import json
import sys

def create_var(name, vtype):
    var_info = {}
    var_info["name"] = name
    var_info["type"] = vtype
    var_info["validation"] = f"isinstance({name}, {vtype})"
    return var_info

def convert_dsl(dsl: str) -> str:
    old_dsl = json.loads(dsl)
    new_dsl = {}
    
    new_dsl["fsm_name"] = old_dsl["fsm_name"]
    new_dsl["config_vars"] = old_dsl["config_vars"]
    new_dsl["variables"] = old_dsl["variables"]
    new_dsl["dsl"] = old_dsl["dsl"]
    
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
            inp_task["message"] = f"Enter value for {iname}, {idesc}"
            inp_task["write_variable"] = iname
            inp_task["datatype"] = "str"
            
            next_task = start_name
            if i < len(new_dsl["config_vars"]) - 1:
                next_task = new_dsl["config_vars"][i + 1]["name"] + "_cnf_t"
            
            inp_task["goto"] = next_task
            inp_task["error_goto"] = next_task
            
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

            jump_list = []
            for t in transitions:
                jump = {}
                jump["condition"] = name + "_code == " + t["code"]
                jump["goto"] = t["goto"]
                jump["description"] = t["description"]
                jump_list.append(jump)
            
            api_result_branch["conditions"] = jump_list
            
            # simulate input tasks
            plugin_name = task["plugin"]["name"]
            plugin_inputs = ""
            
            for k, v in task["plugin"]["inputs"].items():
                if v in self.all_var_list:
                    plugin_inputs += f"{k}: {{{v}}}\\n"
                else:
                    plugin_inputs += f"{k}: {v}\\n"
            
            plugin_outputs = "api code ," +  ", ".join(task["plugin"]["outputs"].keys())
            plugin_desc = task["description"]
            
            common_desc = f"Please enter simulated output of the plugin : {plugin_name}.\\nThe plugin does the following : {plugin_desc}.\\nThe plugin inputs are the following : {plugin_inputs}.\\nProvide values for the following variables : {plugin_outputs}"
            
            first_output_task = {}
            first_output_task["task_type"] = "print"
            first_output_task["name"] = name
            first_output_task["message"] = common_desc
            first_output_task["goto"] = name + "_code_inp_t"
            substitute_task_list.append(first_output_task)
            
            for j, v in enumerate(output_vars):
                otask = {}
                otask["task_type"] = "input"
                otask["name"] = v + "_inp_t"
                otask["message"] = f"Enter value for {v}"
                otask["write_variable"] = v
                
                otask["datatype"] = "str"
                if j == 0:
                    otask["datatype"] = "int"
                
                if v not in all_var_list:
                    var_info = create_var(v, otask["datatype"])
                    new_dsl["variables"].append(var_info)
                
                next_task = api_result_branch["name"]
                if j < len(output_vars) - 1:
                    next_task = output_vars[j + 1] + "_inp_t"
                
                otask["goto"] = next_task
                otask["error_goto"] = next_task
                substitute_task_list.append(otask)
            
            substitute_task_list.append(api_result_branch)
            new_step_insertion.append((i, substitute_task_list))
    
    if len(new_step_insertion) > 0:
        for i in range(len(new_step_insertion) -1, -1, -1):
            pos, nsteps = new_step_insertion[i]
            new_dsl["dsl"].pop(pos)
            
            for j in range(len(nsteps)):
                new_dsl["dsl"].insert(pos + j, nsteps[j])
    
    return json.dumps(new_dsl, indent=4)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            print(convert_dsl(f.read()))
