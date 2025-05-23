import asyncio
import threading
import logging
import importlib
import importlib.util
import os
import sys
import json
import re
import requests
import yaml
import traceback
import ctypes
import urllib

from typing import List, Type, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone

from pwr_studio.representations import PwRStudioRepresentation
from pwr_studio.engines import PwRStudioEngine
from pwr_studio.types import ChangedRepresentation, Representation, Response

# temporary lib imports
from jb_manager_bot import AbstractFSM
from jb_manager_bot.data_models import FSMOutput, MessageType

# need to check and remove the Message class from here
class Message(BaseModel):
    type: str
    content: str


from nl2dsl import NL2DSL
from .utils.codegen import CodeGen
from .utils.test_codegen import TestCodegen
from .utils.nlr_gen import generate_nlr
from .utils.feedback_gen import generate_feedback
from .utils.mermaid_chart import generate_mermaid_chart
from .utils.question_answer import get_answer_or_instruction

# test code runtime
from typing import Dict, Any, Type, List, Tuple, Set, Optional, Literal
from pydantic import BaseModel, Field

import re

credentials = {
    'OPENAI_API_TYPE': os.getenv('OPENAI_API_TYPE', ''),
    'OPENAI_API_ENDPOINT': os.getenv('OPENAI_API_ENDPOINT', ''),
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
    'OPENAI_API_VERSION': os.getenv('OPENAI_API_VERSION', ''),
    'AZURE_CREDENTIAL_SCOPE': os.getenv('AZURE_CREDENTIAL_SCOPE', ''),
    'FAST_MODEL': os.getenv('FAST_MODEL', ''),
    'SLOW_MODEL': os.getenv('SLOW_MODEL', ''),
}

def utcnow():
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()


def empty_callback(**kwargs):
    pass


def extract_plugins(text: str):
    # Sample text containing multiple patterns
    # text = "#plugin(one) some other text #plugin(two) more text #plugin(three)"
    pattern = r"#plugin\((.*?)\)"

    matches: list = re.findall(pattern, text)
    plugins = {}

    for match in matches:
        # if not validators.url(match):
        #     raise Exception(f"Invalid Plugin URL: {match}")

        print(f"Captured URL: {match}")

        match = match.replace("localhost:", "host.docker.internal:")
        match = match.replace("127.0.0.1:", "host.docker.internal:")
        response = requests.get(match)
        file_text = response.content.decode()

        parsed_data = yaml.safe_load(file_text)

        print(parsed_data)

        if "name" not in parsed_data or "description" not in parsed_data:
            raise Exception(f"Invalid Plugin File: {match}")

        plugins[parsed_data["name"]] = parsed_data["description"]

        text = text.replace(f"#plugin({match})", parsed_data["name"], 1)

    return text, plugins

class JBEngine(PwRStudioEngine):

    def __init__(
        self,
        project: str,
        progress,
        credentials: dict = None,
        session_id: str = None,
        istest: bool = False,
    ):
        if not istest:
            super().__init__(project, progress, credentials=credentials)

    def _get_representations(self) -> List[PwRStudioRepresentation]:
        return [NLRep(), DSLRep(), SJSRep(), CodeRep(), TestStateRep()]

    async def _process_utterance(self, text, **kwargs):

        chat_history_strings = kwargs.get("chat_history", [])
        chat_history = [
            Message(type=x.type, content=x.message) for x in chat_history_strings
        ]
        try:
            dsl = json.loads(self._project.representations["dsl"].text)
        except Exception as e:
            dsl = {
                "variables": [],
                "config_vars": [],
                "dsl": [
                    {
                        "task_type": "start",
                        "name": "zero",
                        "goto": "end",
                    },
                    {
                        "task_type": "end",
                        "name": "end",
                        "goto": None,
                    },
                ],
                "fsm_name": "unnamed_fsm",
            }
        description = self._project.representations["description"].text
        diagram = self._project.representations["diagram"].text

        # moderator_res = ModeratePrompt(message=text, model= 'gpt-3.5-turbo-1106')
        # if moderator_res.lower().startswith("yes"):
        #     # content needs moderation
        #     await self._progress(
        #     Response(
        #         type="error",
        #         message="The input is harmful in nature. Please try again."
        #     ))
        #     return
        text, plugins = extract_plugins(text)

        self_inst = self

        answer_or_inst = get_answer_or_instruction(
            dsl=json.dumps(dsl), utterance=text, chat_history=chat_history_strings
        )
        # print(answer_or_inst)

        if answer_or_inst.startswith("Answer:"):
            await self._progress(
                Response(
                    type="output", message=answer_or_inst[7:], project=self._project
                )
            )
            return

        async def async_print(x):
            await self_inst._progress(Response(type="thought", message=x))

        def status_update_callback(x):
            t1 = threading.Thread(target=asyncio.run, args=(async_print(x),))
            t1.start()
            t1.join()

        def status_update_callback_wrapper(event, data):
            if event == "plan_generated":
                status_update_callback(
                    f"Plan successfully generated with {len(data)} steps!🎉 \n\n"
                )
                status_update_callback(f"Updating the program.")
            elif event == "step_update":
                step = data["step"]
                step_number = data["step_number"]
                total_steps = data["total_steps"]
                status_update_callback(
                    f"Executing step {step_number}/{total_steps}. Task: {step['task_id']} of type {step['type']}."
                )
            elif event == "flow_update_completed":
                status_update_callback(f"All steps have been applied successfully!🎉")
                status_update_callback(f"Working on the final touches.")
            elif event == "global_variables_updated":
                status_update_callback(f"Updating Entries!")
            elif event == "config_vars_updated":
                status_update_callback(f"Updating Entries!")
            elif event == "dsl_updated_successfully":
                status_update_callback(f"Program update completed!")

        status_update_callback(f"Thanks for your input! 🚀")
        status_update_callback(f"Preparing a plan to update the program! 📝")
        old_nlr = generate_nlr(dsl)
        nl2dsl = NL2DSL(
            utterance=text,
            dsl=dsl,
            plugins=plugins,
            status_update_callback=status_update_callback_wrapper,
            debug=True,
        )

        nl2dsl.nl2dsl()

        issues = nl2dsl.validate_dsl()

        nlr = generate_nlr(nl2dsl.dsl)
        code = CodeGen(json_data=nl2dsl.dsl).generate_fsm_code()
        status_update_callback(f"Preparing feedback ...")
        feedback = generate_feedback(
            chat_history_strings
            + [
                text,
            ],
            nlr,
            issues,
            old_nlr,
            debug=True,
        )
        chart = generate_mermaid_chart(nl2dsl.dsl["dsl"])

        # user_output = d.change.llm_review

        if nl2dsl.dsl is not None:
            new_dsl = json.dumps(nl2dsl.dsl, indent=4)
            self._project.representations["dsl"].text = new_dsl

            if new_dsl != self._project.representations["dsl"].text:
                self._project.representations["fsm_state"].text = "{}"

        if nlr is not None:
            self._project.representations["description"].text = nlr

        if chart is not None:
            self._project.representations["diagram"].text = chart

        if code is not None:
            self._project.representations["code"].text = code

        program_state = {
            "errors": len(issues["errors"]),
            "warnings": len(issues["warnings"]),
            "optimizations": 0,  # hard coded for now
            "botExperience": "80%",  # hard coded for now
        }
        # TODO fix this at db/contract level
        await self._progress(
            Response(type="dsl_state", message=json.dumps(program_state))
        )

        await self._progress(
            Response(type="output", message=feedback, project=self._project)
        )
        status_update_callback(f"Program update completed! 🎉")

    async def _get_output(self, user_input, **kwargs):
        # to remove trailing new lines
        user_input = user_input.strip()

        msg_queue = []
        def fsm_callback(x: FSMOutput):
            if hasattr(x, "name"):
                plugin_options = x.model_dump()
                plugin_options['type'] = "plugin"
                msg_queue.append(f'{json.dumps(plugin_options)}\xa1')
                return
            if x.message.message_type == MessageType.TEXT:
                msg_queue.append(x.message.text.body)
            if x.message.message_type == MessageType.IMAGE:
                msg_queue.append(x.message.image.url)
                msg_queue.append(x.message.image.caption)
            if x.message.message_type == MessageType.BUTTON:
                msg_queue.append(x.message.button.header)
                msg_queue.append(x.message.button.body)
                msg_queue.append(x.message.button.footer)
                options = {
                    "type": "dropdown",
                    "options": [op.option_text for op in x.message.button.options]
                }
                msg_queue.append(f'{json.dumps(options)}\xa1')
            if x.message.message_type == MessageType.OPTION_LIST:
                msg_queue.append(x.message.option_list.header)
                msg_queue.append(x.message.option_list.body)
                msg_queue.append(x.message.option_list.footer)
                options = {
                    "type": "dropdown",
                    "options": [op.option_text for op in x.message.option_list.options]
                }
                msg_queue.append(f'{json.dumps(options)}\xa1')
            
        def get_input_parts(x: str):
            if x is not None:
                if '\xa1' in x:
                    input_data = x.split('\xa1')[0]
                    try:
                        jobj = json.loads(input_data)
                        return list(jobj["vars"].values())
                    except:
                        return [input_data, ]
                else:
                    return [x, ]
            else:
                return [None, ]

        if user_input == "_reset_chat_" or user_input == "/start" or user_input.lower() == "hi":
            # restart the bot
            await self._progress(
                Response(type="thought", message="Starting new bot instance", project=self._project)
            )
            user_input = None
            self._project.representations["fsm_state"].text = "{}"

        is_bot_end = False
        try:
            dsl_obj = json.loads(self._project.representations["dsl"].text)
            test_code = TestCodegen(json_data=dsl_obj).generate_fsm_code()

            # load class via exec
            #gen_class_dict = {}
            #exec(test_code, globals(), gen_class_dict)
            #tclz = gen_class_dict[dsl_obj["fsm_name"]]

            code_hash = str(ctypes.c_size_t(hash(test_code)).value)
            module_name = "mod_" + code_hash
            module_dir = "/tmp/pkg_" + code_hash
            file_path = module_dir + "/fsm.py"

            # TODO : handle concurrency
            if not os.path.isdir(module_dir):
                os.mkdir(module_dir)
                with open(file_path, "w") as f:
                    f.write(test_code)
                    open(module_dir + "/__init__.py", "a").close()

            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module

            spec.loader.exec_module(module)
            tclz = getattr(module, dsl_obj["fsm_name"])

            fsm_state = self._project.representations["fsm_state"].text
            state = None
            if fsm_state and fsm_state != "{}":
                state = json.loads(fsm_state)

            input_parts = get_input_parts(user_input)
            for inp in input_parts:
                if isinstance(inp, dict):
                    inp = json.dumps(inp)
                state = tclz.run_machine(fsm_callback, inp, None, credentials, state)

            self._project.representations["fsm_state"].text = json.dumps(state)

            if state and state["main"]["state"] == "zero":
                is_bot_end = True

        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
            await self._progress(
                Response(type="thought", message="Error in processing dsl", project=self._project)
            )

        if len(msg_queue) > 0:
            for m in msg_queue:
                await self._progress(Response(type="output", message=m, project=self._project))

        if is_bot_end:
            await self._progress(Response(type="thought", message="The bot has successfully completed. Please restart to test again.", project=self._project))
        elif len(msg_queue) < 1:
            await self._progress(Response(type="thought", message="Enter input to proceed.", project=self._project))

    async def _process_representation_edit(self, edit: ChangedRepresentation, **kwargs):
        pass

    async def _process_import(self, **kwargs):
        dsl = self._project.representations["dsl"].text

        self.initalize()
        self._project.representations["dsl"].text = dsl

        nl2dsl = NL2DSL(
            utterance="None",
            dsl=json.loads(dsl),
            plugins={},
        )

        # comment out for now
        issues = nl2dsl.validate_dsl()

        code = CodeGen(json_data=nl2dsl.dsl).generate_fsm_code()
        nlr = generate_nlr(nl2dsl.dsl)

        self_inst = self

        async def async_print(x):
            await self_inst._progress(Response(type="thought", message=x))

        def status_update_callback(x):
            t1 = threading.Thread(target=asyncio.run, args=(async_print(x),))
            t1.start()
            t1.join()

        if dsl is not None:
            self._project.representations["dsl"].text = dsl

        if nlr is not None:
            self._project.representations["description"].text = nlr

        # if d.change.diagram is not None:
        #     self._project.representations['diagram'].text = d.change.diagram

        if code is not None:
            self._project.representations["code"].text = code

        program_state = {
            "errors": issues["errors"],
            "warnings": issues["warnings"],
            "optimizations": 0,  # hard coded for now
            "botExperience": "80%",  # hard coded for now
        }
        await self._progress(
            Response(type="dsl_state", message=json.dumps(program_state))
        )

        await self._progress(
            Response(
                type="output",
                message="The dsl has been successfully imported!",
                project=self._project,
            )
        )

    def process_updated_representations(self, output):
        pass

    def _process_attachment(self):
        pass


#####


class NLRep(PwRStudioRepresentation):
    def _get_initial_values(self):
        return Representation(name="description", text="", type="md", sort_order=4)


class SJSRep(PwRStudioRepresentation):
    def _get_initial_values(self):
        return Representation(name="diagram", text="", type="image", sort_order=3)


# TODO: Fix the intiialization value
class DSLRep(PwRStudioRepresentation):
    def _get_initial_values(self):
        return Representation(name="dsl", text="""""".strip(), type="md", sort_order=2)


class CodeRep(PwRStudioRepresentation):
    def _get_initial_values(self):
        return Representation(name="code", text="", type="md", sort_order=1)

class TestStateRep(PwRStudioRepresentation):
    def _get_initial_values(self):
        return Representation(name="fsm_state", text="{}", type="md", sort_order=0)