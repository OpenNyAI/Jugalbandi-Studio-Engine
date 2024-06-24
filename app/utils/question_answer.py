import json
import argparse
from .llm import llm
from nl2dsl import chat_completion_request, task_types_info as TASK_TYPES_INFO


def get_answer_or_instruction(dsl, utterance, chat_history=""):
    system_prompt = """You are a developer bot that is making changes to a program flow called a domain specific language (DSL). These changes are made based on instructions provided by a user utterance. 
    At the same time, you also help the user with any questions they have about the program flow. Your job is to determine whether the user is asking a question or providing instructions for the program flow.
    If the user is asking a question, you should begin your response with "Answer:" and provide an answer to the question, taking into account the description of the program flow below. Your answer should be snappy and to the point, think the size of an SMS.
    Your answer is aimed at a domain expert who is not too familiar with programming concepts.
    If the question asked is irrelevant to the program flow, you should respond with "Answer:I'm sorry, I can't help with that. I can only help with questions related to the program flow or instructions to modify it."
    If the user is providing instructions for the program flow, you should begin your response with "Instruction". No need to provide an answer to the user's question in this case.

    ## Program Flow Structure Info:
    {TASK_TYPES_INFO}

    ## Flow:
    {dsl}

    ## Chat History:
    {chat_history}
    """

    user_prompt = """### User Utterance:
    {utterance}
    """

    messages = [
        {
            "role": "system",
            "content": system_prompt.format(
                dsl=dsl, TASK_TYPES_INFO=TASK_TYPES_INFO, chat_history=chat_history
            ),
        },
        {"role": "user", "content": user_prompt.format(utterance=utterance)},
    ]

    chat_response = chat_completion_request(messages)
    return chat_response.choices[0].message.content

