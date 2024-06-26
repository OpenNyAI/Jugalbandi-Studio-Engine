import json

colors = {
    "start": {
        "fill": "#b0c4de",
        "stroke": "#778899",
        "text_color": "#000000",
    },  # LightSteelBlue for start
    "print": {
        "fill": "#98fb98",
        "stroke": "#2e8b57",
        "text_color": "#000000",
    },  # PaleGreen for print
    "input": {
        "fill": "#add8e6",
        "stroke": "#4682b4",
        "text_color": "#000000",
    },  # LightBlue for input
    "operation": {
        "fill": "#d3d3d3",
        "stroke": "#a9a9a9",
        "text_color": "#000000",
    },  # LightGray for operation
    "condition": {
        "fill": "#d3d3d3",
        "stroke": "#a9a9a9",
        "text_color": "#000000",
    },  # LightGray for condition
    "plugin": {
        "fill": "#dda0dd",
        "stroke": "#ba55d3",
        "text_color": "#000000",
    },  # Plum for plugin
    "end": {
        "fill": "#b0c4de",
        "stroke": "#778899",
        "text_color": "#000000",
    },  # LightSteelBlue for end
}

success_arrow = "-->"
fail_arrow = "-.->"
default_arrow = "==>"


def split_long_text(text, max_words=10):
    words = text.split(" ")
    return "<br>".join(
        [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]
    )


def generate_mermaid_chart(flow):
    nodes = []
    links = []

    def create_node(task, task_id):
        task_type = task.get("task_type")
        if task_type == "print":
            label = task.get("message", task.get("name"))
            label = split_long_text(label)
        elif task_type == "input":
            label = task.get("message", task.get("name"))
            label = split_long_text(label)
        elif task_type == "operation":
            label = task.get("description", task.get("name"))
            label = label.replace("\n", "<br>")
            label += f"<br>{task.get('expression')}"
        elif task_type == "condition":
            label = task.get("description", task.get("name"))
        elif task_type == "plugin":
            label = task.get("description", task.get("name"))
        else:
            label = task.get("name")

        node = f'`{task_id}`["{label}"]:::task{task_type}'
        nodes.append(node)
        return task_id

    def process_task(task, task_id):
        create_node(task, task_id)
        task_type = task["task_type"]

        if "goto" in task:
            next_task = task["goto"]
            if next_task:
                links.append(f"`{task_id}` {success_arrow} `{next_task}`")
        if "error_goto" in task:
            error_task = task["error_goto"]
            if error_task:
                links.append(f"`{task_id}` {fail_arrow} `{error_task}`")
        if "else_goto" in task:
            else_task = task["else_goto"]
            else_description = split_long_text(task.get("else_description", "else"))
            if else_task:
                links.append(
                    f'`{task_id}` {fail_arrow}|"{else_description}"| `{else_task}`'
                )

        if "transitions" in task:
            for transition in task["transitions"]:
                if "condition" in transition:
                    condition = transition.get("condition", "")
                elif "code" in transition:
                    condition = transition.get("code", "")
                next_task = transition["goto"]
                if "description" in transition:
                    condition = transition.get("description", condition)
                elif "condition_description" in transition:
                    condition = transition.get("condition_description", condition)
                if next_task:
                    condition = condition.replace('"', '\\"')
                    condition = split_long_text(condition)
                    links.append(
                        f'`{task_id}` {default_arrow} |"{condition}"| `{next_task}`'
                    )
        if "conditions" in task:
            for transition in task["conditions"]:
                if "condition" in transition:
                    condition = transition.get("condition", "")
                elif "code" in transition:
                    condition = transition.get("code", "")
                if "description" in transition:
                    condition = transition.get("description", condition)
                elif "condition_description" in transition:
                    condition = transition.get("condition_description", condition)
                next_task = transition["goto"]
                if next_task:
                    condition = condition.replace('"', '\\"')
                    condition = split_long_text(condition)
                    links.append(
                        f'`{task_id}` {default_arrow}|"{condition}"| `{next_task}`'
                    )

    for task in flow:
        task_id = task.get("name")
        process_task(task, task_id)

    mermaid_chart = ["graph TD"]
    mermaid_chart.extend(nodes)
    mermaid_chart.extend(links)
    for task_type, color in colors.items():
        fill = color["fill"]
        stroke = color["stroke"]
        text_color = color["text_color"]
        mermaid_chart.append(
            f"classDef task{task_type} fill:{fill},stroke:{stroke},stroke-width:2px,color:{text_color},max-width:150px,wrap:true,font-size:15px;"
        )

    return "\n".join(mermaid_chart)
