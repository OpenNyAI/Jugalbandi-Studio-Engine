import json
import os
import openai
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored


# @retry(wait=wait_random_exponential(
#     multiplier=10,
#     max=120),
#     stop=stop_after_attempt(1))
def llm(messages, **kwargs):
    client = openai.Client(
        api_key=os.environ["OPENAI_API_KEY"],
    )

    kwargs["model"] = kwargs.get("model", "gpt-4-1106-preview")
    kwargs["messages"] = messages
    args = {
        k: v
        for k, v in kwargs.items()
        if k in ["model", "messages", "temperature", "tools", "stream"]
    }

    if kwargs.get("debug", False):
        others = {
            k: v for k, v in args.items() if k not in ["messages", "callback", "debug"]
        }
        print(colored(others, "yellow"))
        for message in args["messages"]:
            print(colored(message["role"], "green"))
            print(colored(message["content"], "yellow"))

    if args.get("temperature", None) is None:
        args["temperature"] = 1e-6

    completions = client.chat.completions.create(**args)

    if args.get("stream", False):
        full_response = ""
        for chunk in completions:
            for choice in chunk.choices:
                if choice.finish_reason == "stop":
                    break
                if choice.delta.content is not None:
                    kwargs["callback"](choice.delta.content)
                    full_response += choice.delta.content
        return full_response
    elif args.get("tools", None) is None:
        return completions.choices[0].message.content
    else:
        if kwargs.get("debug", False):
            print(colored(completions.choices[0].message, "yellow"))
        if completions.choices[0].message.tool_calls is None:
            return {"function": None, "message": completions.choices[0].message.content}
        fn = completions.choices[0].message.tool_calls[0].function
        return {"function": fn.name, "arguments": json.loads(fn.arguments)}


def sm(prompt):
    return {"role": "system", "content": prompt}


def um(prompt):
    return {"role": "user", "content": prompt}


def am(prompt):
    return {"role": "assistant", "content": prompt}


def fn(name, description, params, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {k: v for k, v in params.items()},
                "required": required,
            },
        },
    }


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    result = llm(
        [
            sm("Respond by using functions only"),
            um("The story needs to have a good ending"),
        ],
        tools=[
            fn(
                "update_story",
                "Update the current story",
                {
                    "change": {
                        "type": "string",
                        "description": "instructions from the user",
                    }
                },
                ["change"],
            ),
            fn(
                "update_characters",
                "Update the characters in the story",
                {
                    "change": {
                        "type": "string",
                        "description": "instructions from the user",
                    }
                },
                ["change"],
            ),
            fn(
                "update_scenes",
                "Update the scenes in the story",
                {
                    "scene_number": {"type": "integer", "description": "scene number"},
                    "change": {
                        "type": "string",
                        "description": "instructions from the user",
                    },
                },
                ["change"],
            ),
        ],
    )

    print(result)
