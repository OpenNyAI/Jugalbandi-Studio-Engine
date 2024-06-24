from .llm import llm, sm, um


def generate_diff(old_nlr, new_nlr, **kwargs):
    template_str = f"""You are a developer bot that is developing a program as per the following user instruction. 
The program plan has been updated.
Here is the older plan: {old_nlr}

Here is the updated plan: {new_nlr}

Write one point on the steps that have been completed or updated in the new plan. Return in atmost 10 words. Think step by step. Be clear and concise.
"""
    result = llm(
        [
            sm(
                "You are a developer bot that is helping users to understand the changes in the program plan."
            ),
            um(template_str),
        ],
    )
    if result and len(result) > 0:
        return result
    else:
        return "The program has been updated as per instruction"


def generate_future_steps(user_history, dsl_desc, errors_dict, **kwargs):
    errors = errors_dict.get("errors", [])
    errors.extend(errors_dict.get("warnings", []))
    errors.extend(errors_dict.get("info", []))

    if not user_history or len(user_history) < 1:
        return ""

    if not dsl_desc or len(dsl_desc) < 1:
        return ""

    error_string = ""
    if errors and len(errors) > 0:
        error_string += "Logical errors found in the program plan :"
        for e in errors:
            error_string += f"\n- {e}"

    template_str = """You are a developer bot that is developing a program as per the following user instruction : 
{0}

Here is the plan of how the program should be written with various tasks listed out:
{1}
{2}

Now think as a developer and list out ideas to improve the program. Restrict to ideas that make the program logically complete or that add the important functionality.
Ignore handling corner cases. Ignore validating variables. Fix logical errors if present. If there are no issues, dont report ideas. Mention step names that are closely related to the idea.
Return at most 3 bullet points. Each bullet point should be in simple english and have at most 10 words. Think step by step. Be clear and concise. Dont repeat similar ideas."""

    user_instruction = ""
    for i, inst in enumerate(user_history):
        user_instruction += f"{i}: {inst}\n"
    result = llm(
        [
            sm(
                "You are a developer bot that is helping users improve a program by providing helpful suggestions"
            ),
            um(template_str.format(user_instruction, dsl_desc, error_string)),
        ],
    )

    if result and len(result) > 0:
        return f"Here are some next steps that can be tried:\n {result}"
    else:
        return ""


def generate_feedback(user_history, dsl_desc, errors, old_nlr, **kwargs):
    diff = generate_diff(old_nlr, dsl_desc)
    feedback = generate_future_steps(user_history, dsl_desc, errors, **kwargs)
    return f"{diff}\n{feedback}"
