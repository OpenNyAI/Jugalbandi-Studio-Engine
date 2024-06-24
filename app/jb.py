import asyncio
import threading
import importlib
import os
import sys
import json
import re
import requests
import yaml
import traceback

from typing import List, Type, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone


from pwr_studio.representations import PwRStudioRepresentation
from pwr_studio.engines import PwRStudioEngine
from pwr_studio.types import ChangedRepresentation, Representation, Response

# temporary lib imports
from .jb_manager_bot import AbstractFSM, FSMOutput

# need to check and remove the Message class from here
class Message(BaseModel):
    type: str
    content: str


from nl2dsl import NL2DSL
from .utils.codegen import CodeGen
from .utils.nlr_gen import generate_nlr
from .utils.feedback_gen import generate_feedback
from .utils.mermaid_chart import generate_mermaid_chart
from .utils.convert_dsl_for_test import convert_dsl

# test code runtime
from typing import Dict, Any, Type, List, Tuple, Set, Optional, Literal
from pydantic import BaseModel, Field
from .jb_manager_bot import (
    AbstractFSM,
    FSMOutput,
)
import re

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
                        "name": "start",
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

        async def async_print(x):
            await self_inst._progress(Response(type="thought", message=x))

        def status_update_callback(x):
            t1 = threading.Thread(target=asyncio.run, args=(async_print(x),))
            t1.start()
            t1.join()

        def status_update_callback_wrapper(event, data):
            if event == "plan_generated":
                status_update_callback(
                    f"Plan successfully generated! 🎉 ({len(data)} steps)\n\n"
                )
                status_update_callback(f"Applying the plan...")
            elif event == "step_update":
                step = data["step"]
                step_number = data["step_number"]
                status_update_callback(
                    f"Applying step {step_number}({step['type']}) of the plan for task {step['task_id']}..."
                )
            elif event == "flow_update_completed":
                status_update_callback(
                    f"All steps in the plan have been applied successfully! 🎉"
                )
                status_update_callback(f"Generating the final program ...")

        status_update_callback(f"Generating a plan to update the program ...")

        nl2dsl = NL2DSL(
            utterance=text,
            dsl=dsl,
            plugins=plugins,
            status_update_callback=status_update_callback_wrapper,
            debug=True,
        )

        nl2dsl.nl2dsl()

        errors = nl2dsl.validate_dsl()
        nlr = generate_nlr(nl2dsl.dsl)
        code = CodeGen(json_data=nl2dsl.dsl).generate_fsm_code()
        feedback = generate_feedback(
            chat_history_strings
            + [
                text,
            ],
            nlr,
            errors,
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
            "errors": len(errors),
            "warnings": 0,
            "optimizations": 0,
            "botExperience": "80%",
        }
        # TODO fix this at db/contract level
        await self._progress(
            Response(type="dsl_state", message=json.dumps(program_state))
        )

        await self._progress(
            Response(type="output", message=feedback, project=self._project)
        )

    async def _get_output(self, user_input, **kwargs):
        msg_queue = []
        def fsm_callback(x: FSMOutput):
            if x.message_data.header:
                msg_queue.append(x.message_data.header)
            if x.message_data.body:
                msg_queue.append(x.message_data.body)
            if x.message_data.footer:
                msg_queue.append(x.message_data.footer)
            if x.options_list:
                msg_queue.append(x.options_list)
            if x.media_url:
                msg_queue.append(x.media_url)

        if user_input == "_reset_chat_" or user_input == "/start":
            # restart the bot
            await self._progress(
                Response(type="thought", message="Starting new bot instance", project=self._project)
            )
            user_input = None
            self._project.representations["fsm_state"].text = "{}"

        try:
            test_dsl = convert_dsl(self._project.representations["dsl"].text)
            dsl_obj = json.loads(test_dsl)
            if dsl_obj['dsl'][0]['name'] != 'zero':
                inst = {}
                inst['task_type'] = 'start'
                inst['name'] = 'zero'
                inst['goto'] = dsl_obj['dsl'][0]['name']
                
                if dsl_obj['dsl'][0]['task_type'] == 'start':
                    dsl_obj['dsl'][0]['task_type'] = 'print'
                    dsl_obj['dsl'][0]['message'] = ''
                
                dsl_obj['dsl'].insert(0, inst)
            
            test_code = CodeGen(json_data=dsl_obj).generate_fsm_code()

            gen_class_dict = {}
            exec(test_code, globals(), gen_class_dict)
            x = gen_class_dict[dsl_obj["fsm_name"]]
            
            fsm_state = self._project.representations["fsm_state"].text
            state = None
            if fsm_state and fsm_state != "{}":
                state = json.loads(fsm_state)

            state = x.run_machine(fsm_callback, user_input, None, {}, state)

            self._project.representations["fsm_state"].text = json.dumps(state)
            print('@@@')
            print(self._project.representations["fsm_state"].text)

        except:
            print(traceback.format_exc())
            await self._progress(
                Response(type="thought", message="Error in processing dsl", project=self._project)
            )
        
        if len(msg_queue) > 0:
            for m in msg_queue:
                await self._progress(Response(type="output", message=m, project=self._project))
        else:
            await self._progress(Response(type="thought", message=".", project=self._project))

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
        # nl2dsl.validate_dsl()

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
            "errors": 0,
            "warnings": 0,
            "optimizations": 0,
            "botExperience": "80%",
        }
        # await self._progress(
        #     Response(
        #         # type="dsl_state",
        #         message=json.dumps(program_state)
        #     ))

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