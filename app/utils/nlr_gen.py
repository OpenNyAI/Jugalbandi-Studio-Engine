import json


def generate_nlr(dsl):
    def snake_to_camel_case(snake_str):
        components = snake_str.split("_")
        return " ".join(x.title() for x in components)

    def get_config_variable_info(var, index):
        name = var.get("name", "Unknown")
        description = var.get("description", "No description provided")
        return f"{index}. {name}\n\n    {description}"

    def get_variable_info(var, index):
        name = var.get("name", "Unknown")
        validation = var.get("description", var.get("validation", "Unknown"))
        return f"{index}. {name}:\n\n    {validation}"

    def get_task_info(task, index):
        task_name = task.get("name", "Unknown Step")
        task_name = snake_to_camel_case(task_name)
        task_info = [f"### {index}. {task_name}"]

        if "message" in task and task["message"]:
            task_info.append(f"**Message**: {task['message']}")

        if "plugin" in task:
            plugin_info = task.get("plugin", {})
            task_info.append(f"**Uses Plugin**: {plugin_info.get('name', 'Unknown')}")

        if "options" in task:
            options = ", ".join(task["options"])
            task_info.append(f"**Options**: {options}")

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
                    "This step asks the user to choose from a list of options."
                )
            else:
                explanation = "This step asks the user to enter information, which is then stored for further use."
            if "write_variable" in task:
                explanation += f" The user's input is saved in the variable named `{task['write_variable']}`."
        elif task_type == "plugin":
            plugin_info = task.get("plugin", {})
            explanation = f"This step calls a plugin named `{plugin_info.get('name', 'Unknown')}`."

            if "inputs" in plugin_info:
                explanation += "\n\nInput Variables:\n"
                explanation += "\n| Plugin Parameter | Workflow Variable |\n|---|---|\n"
                inputs = "\n".join(
                    [
                        f"| `{k}` | `{v}` |"
                        for k, v in plugin_info.get("inputs", {}).items()
                    ]
                )
                explanation += inputs

            if "outputs" in plugin_info:
                explanation += "\n\nOutput Variables:\n\n"
                explanation += "\n| Plugin Parameter | Workflow Variable |\n|---|---|\n"
                outputs = "\n".join(
                    [
                        f"| `{k}` | `{v}` |"
                        for k, v in plugin_info.get("outputs", {}).items()
                    ]
                )
                explanation += outputs
        elif task_type == "goto":
            explanation = f"This step moves to the next step named `{task.get('goto', 'the next step')}`."
        elif task_type == "condition":
            explanation = "This step checks a specific condition and decides the next step based on whether the condition is met."
        elif task_type == "operation":
            explanation = "This step performs the above operation."

        return explanation

    def get_transitions_explanation(task):
        task_type = task.get("task_type", "Unknown")
        next_step = task.get("goto", "None")

        if task_type == "operation":
            return f"Moves to `{next_step}` after operation."
        elif task_type == "print":
            return f"Moves to `{next_step}` after displaying the message."
        elif task_type == "input":
            success_step = task.get("goto", "None")
            error_step = task.get("error_goto", "None")
            return f"Moves to `{success_step}` if input is valid, otherwise to `{error_step}`."
        elif task_type == "plugin":
            transitions_info = "The plugin transitions to the next steps are:\n\n"
            transitions_info += (
                "\n| Transition Code |  Description | Next Step |\n|---|---|---|\n"
            )
            transition = "\n".join(
                [
                    f"| {t.get('code', 'Unknown')} | {t.get('description', 'No description')} | {t.get('goto', 'Unknown')} |"
                    for t in task.get("transitions", [])
                ]
            )
            transitions_info += transition
            return "".join(transitions_info)
        elif task_type == "condition":
            transitions_info = "The conditions to transition to the next steps are:\n\n"
            transitions_info += (
                "\n| Condition | Description | Next Step |\n|---|---|---|\n"
            )

            transition = "\n".join(
                [
                    f"| {t.get('condition', 'Unknown')} | {t.get('description', 'No description')} | {t.get('goto', 'Unknown')} |"
                    for t in task.get("conditions", [])
                ]
            )
            transitions_info += transition
            return "".join(transitions_info)

        return "No specific transitions."

    nlr = []

    if "dsl" in dsl:
        index = 0
        for task in dsl["dsl"]:
            if task.get("task_type") == "start" or task.get("task_type") == "end":
                continue
            index += 1
            task_info = get_task_info(task, index)
            task_explanation = get_task_explanation(task)
            transitions_explanation = get_transitions_explanation(task)
            nlr.append(
                f"{task_info}\n\n{task_explanation}\n\n{transitions_explanation}"
            )

    if "config_vars" in dsl:
        nlr.append("## 2. Configuration Variables")
        for index, var in enumerate(dsl["config_vars"], start=1):
            nlr.append(get_config_variable_info(var, index))

    if "variables" in dsl:
        nlr.append("## 3. Variables")
        for index, var in enumerate(dsl["variables"], start=1):
            nlr.append(get_variable_info(var, index))

    nlr_str = "\n".join(nlr)
    return nlr_str.strip()
