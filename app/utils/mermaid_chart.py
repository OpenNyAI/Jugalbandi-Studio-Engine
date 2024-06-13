import json

colors = {
    "start": "#8B0000",  # Dark red for start
    "print": "#006400",  # Dark green for print
    "input": "#00008B",  # Dark blue for input
    "operation": "#8B4513",  # SaddleBrown for operation
    "condition": "#4682B4",  # SteelBlue for condition
    "plugin": "#8B008B",  # DarkMagenta for plugin
    "end": "#2F4F4F",  # DarkSlateGray for end
}


def generate_mermaid_chart(flow):
    nodes = []
    links = []

    def create_node(task, task_id):
        task_type = task.get("task_type")
        label = task.get("message", task.get("name"))
        color = colors.get(task_type, "#fff,#fff")

        node = f'`{task_id}`["{label}"]:::task{task_type}'
        nodes.append(node)
        return task_id

    def process_task(task, task_id):
        create_node(task, task_id)
        task_type = task["task_type"]

        if "goto" in task:
            next_task = task["goto"]
            if next_task:
                links.append(f"`{task_id}` --> `{next_task}`")
        if "error_goto" in task:
            error_task = task["error_goto"]
            if error_task:
                links.append(f"`{task_id}` -->|validation fail| `{error_task}`")
        if "transitions" in task:
            for transition in task["transitions"]:
                if "condition" in transition:
                    condition = transition.get("condition", "")
                if "code" in transition:
                    condition = transition.get("code", "")
                next_task = transition["goto"]
                if next_task:
                    links.append(f"`{task_id}` -->|{condition}| `{next_task}`")

    for task in flow:
        task_id = task.get("name")
        process_task(task, task_id)

    mermaid_chart = ["graph TD"]
    mermaid_chart.extend(nodes)
    mermaid_chart.extend(links)
    for task_type, color in colors.items():
        mermaid_chart.append(
            f"classDef task{task_type} fill:{color},stroke:#000,stroke-width:2px,color:#fff,max-width:200px,wrap:true,font-size:15px;"
        )

    return "\n".join(mermaid_chart)
