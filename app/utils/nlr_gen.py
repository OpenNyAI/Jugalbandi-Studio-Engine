import json


def generate_nlr(dsl):
    def get_config_variable_info(var):
        name = var.get("name", "Unknown")
        description = var.get("description", "No description provided")
        return f"- **Name**: {name}\n\n\t**Description**: {description}"

    def get_variable_info(var, if_config=False):
        name = var.get("name", "Unknown")
        var_type = var.get("type", "Unknown")
        description = var.get("description", "No description provided")
        return f"- **Name**: {name}\n\n\t**Type**: {var_type}\n\n  **Validation**: {description}"

    def get_task_info(task):
        task_info = []

        if "message" in task and task["message"]:
            task_info.append(f"**Message**: {task['message']}\n\n")

        # if "read_variables" in task:
        #     read_vars = ", ".join(task["read_variables"])
        #     task_info.append(f"**Uses Data From**: {read_vars}")

        # if "write_variables" in task:
        #     write_vars = ", ".join(task["write_variables"])
        #     task_info.append(f"**Saves Data To**: {write_vars}")

        if "plugin" in task:
            plugin_info = task.get("plugin", {})
            task_info.append(f"**Uses Plugin**: {plugin_info.get('name', 'Unknown')}")

        if "options" in task:
            options = ", ".join(task["options"])
            task_info.append(f"\n**Options**: {options}")

        # if "description" in task:
        #     task_info.append(f"**Description**: {task['description']}\n")

        return "\n".join(task_info)

    def get_task_explanation(task):
        task_type = task.get("task_type", "Unknown")
        explanation = ""

        if task_type == "print":
            explanation = "This step shows a message to the user, providing important information or instructions."
        elif task_type == "input":
            options = task.get("options", None)
            if options:
                explanation = (
                    "This step asks the user to choose from a list of options. "
                )
            else:
                explanation = "This step asks the user to enter information, which is then stored for further use."
            if "write_variable" in task:
                explanation += f" The user's input is saved in the variable named `{task['write_variable']}` and must be in text `{task['datatype']}` format."
        elif task_type == "plugin":
            plugin_info = task.get("plugin", {})
            explanation = f"\n\nThis step calls a plugin named `{plugin_info.get('name', 'Unknown')}` to perform specific operations.\n\n"
            if "inputs" in plugin_info and "outputs" in plugin_info:
                explanation += "The plugin uses the following inputs mapped from the workflow variables:\n\n"
                explanation += "\n\n".join(
                    [
                        f"- `{k}` (plugin parameter) mapped from `{v}` (workflow variable)"
                        for k, v in plugin_info.get("inputs", {}).items()
                    ]
                )
                explanation += "\n\nThe plugin provides the following outputs mapped to the workflow variables:\n\n"
                explanation += "\n\n".join(
                    [
                        f"- `{k}` (plugin parameter) mapped to `{v}` (workflow variable)"
                        for k, v in plugin_info.get("outputs", {}).items()
                    ]
                )

        elif task_type == "goto":
            explanation = f"This step moves to the next step named `{task.get('goto', 'the next step')}`."
        elif task_type == "condition":
            explanation = "This step checks a specific condition and decides the next step based on whether the condition is met.\n\n"
        elif task_type == "operation":
            explanation = "This step performs the above operation."

        return f"\n{explanation}"

    def get_transitions_explanation(task):
        task_type = task.get("task_type", "Unknown")
        if task_type == "operation":
            next_step = task.get("goto", "None")
            return f"Once the operation is performed, the workflow moves to the next step: `{next_step}` automatically."
        if task_type == "print":
            next_step = task.get("goto", "None")
            return f"\n\nAfter displaying the message, the workflow moves to the next step: `{next_step}`."
        elif task_type == "input":
            success_step = task.get("goto", "None")
            error_step = task.get("error_goto", "None")
            transition = "The workflow moves to the next step based on:\n\n"
            transition += f" - If the input is valid, the workflow moves to the next step: `{success_step}`.\n"
            transition += f" - If the input is invalid, it moves to: `{error_step}`."
            return transition
        elif task_type == "plugin":
            transitions_info = []
            transitions_info.append(f"\n\nThe plugin transition to the next steps are:")

            for t in task["transitions"]:
                transition_code = t.get("code", "Unknown")
                transition_goto = t.get("goto", "Unknown")
                transition_description = t.get("description", "No description")
                transitions_info.append(
                    f"\n\n - If {transition_description}({transition_code}), then go to `{transition_goto}`"
                )
            return "\n".join(transitions_info)
        elif task_type == "condition":
            transitions_info = []
            transitions_info.append(
                f"\n\nThe conditions to transition to the next steps are:\n\n"
            )
            for t in task["conditions"]:
                transition_code = t.get("condition", "Unknown")
                transition_goto = t.get("goto", "Unknown")

                transitions_info.append(
                    f"If `{transition_code}` then go to `{transition_goto}`.\n\n"
                )
            return "\n - ".join(transitions_info)
        return ""  # "No specific conditions to transition to another step."

    nlr = []

    if "dsl" in dsl:
        nlr.append("\n## Workflow")
        for task in dsl["dsl"]:
            if task.get("task_type") == "start" or task.get("task_type") == "end":
                continue
            nlr.append(f"\n### Step: {task.get('name', 'Unknown Step')}")
            task_info = get_task_info(task)
            task_explanation = get_task_explanation(task)
            transitions_explanation = get_transitions_explanation(task)
            nlr.append(f"{task_info}\n{task_explanation}\n{transitions_explanation}")

    if "config_variables" in dsl:
        nlr.append("## Configuration Variables")
        for var in dsl["config_variables"]:
            nlr.append(get_config_variable_info(var))

    if "variables" in dsl:
        nlr.append("\n## Variables")
        for var in dsl["variables"]:
            nlr.append(get_variable_info(var))
    nlr_str = "\n".join(nlr)
    return nlr_str.replace("\n\n", "\n").strip()


if __name__ == "__main__":
    # with open("addition-logic/step1/gold.json") as f:
    with open("car-wash/step1/gold.json") as f:
        dsl = json.load(f)
    print(generate_nlr(dsl))
