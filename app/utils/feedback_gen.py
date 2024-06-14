from .llm import llm, sm, um


def generate_feedback(user_history, dsl_desc, errors, **kwargs):
    if kwargs.get("debug", False):
        print("Generating feedback for the user")
        print("Length of DSL description:", len(dsl_desc))
        print("Length of User history:", len(user_history))

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
    if kwargs.get("debug", False):
        print("User instruction:", user_instruction)
    result = llm(
        [
            sm(
                "You are a developer bot that is helping users improve a program by providing helpful suggestions"
            ),
            um(template_str.format(user_instruction, dsl_desc, error_string)),
        ],
        debug=True,
    )

    if kwargs.get("debug", False):
        print("Feedback generated:", result)

    if result and len(result) > 0:
        return f"Here are some next steps that can be tried:\n {result}"
    else:
        return "The program has been updated as per instruction"
