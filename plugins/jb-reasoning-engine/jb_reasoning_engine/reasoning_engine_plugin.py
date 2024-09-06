from enum import Enum
from typing import Any, Dict, Optional
from jb_manager_bot import AbstractFSM
from jb_manager_bot.abstract_fsm import Variables
from jb_manager_bot.data_models import (
    Status,
)
from jb_manager_bot.parsers.utils import LLMManager


class reasoning_engineReturnStatus(Enum):
    SUCCESS = "success"
    BAD_REQUEST = "bad_request"
    UNAUTHORISED = "unauthorised"
    SERVER_ERROR = "server_error"


class reasoning_enginePluginVariables(Variables):
    QUERY: Optional[str] = None
    SYSTEM_PROMPT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = None
    AZURE_OPENAI_API_ENDPOINT: Optional[float] = None
    MODEL: Optional[str] = None
    RESPONSE: Optional[str] = None


class reasoning_engine(AbstractFSM):

    states = [
        "zero",
        "call_llm",
        "end",
    ]
    transitions = [
        {"source": "zero", "dest": "call_llm", "trigger": "next"},
        {
            "source": "call_llm",
            "dest": "end",
            "trigger": "next",
        },
    ]
    conditions = set()
    output_variables = {"RESPONSE"}
    variable_names = reasoning_enginePluginVariables
    return_status_values = reasoning_engineReturnStatus

    def __init__(self, send_message: callable, credentials: Dict[str, Any] = None):
        if credentials is None:
            credentials = {}

        self.credentials = credentials

        self.variables = self.variable_names()
        self.return_status_values = self.return_status_values.SUCCESS
        super().__init__(send_message)

    def on_enter_call_llm(self):
        self.status = Status.WAIT_FOR_ME
        llm_query = getattr(self.variables, "QUERY")
        system_prompt = getattr(self.variables, "SYSTEM_PROMPT")
        azure_openai_api_key = getattr(self.variables, "AZURE_OPENAI_API_KEY")
        azure_openai_api_version = getattr(self.variables, "AZURE_OPENAI_API_VERSION")
        azure_openai_api_endpoint = getattr(self.variables, "AZURE_OPENAI_API_ENDPOINT")
        model = getattr(self.variables, "MODEL")

        llm_response = LLMManager.llm(
            messages=[
                LLMManager.sm(system_prompt),
                LLMManager.um(llm_query),
            ],
            azure_openai_api_key=azure_openai_api_key,
            azure_openai_api_version=azure_openai_api_version,
            azure_openai_api_endpoint=azure_openai_api_endpoint,
            model=model,
        )

        setattr(self.variables, "RESPONSE", llm_response)
        self.status = Status.MOVE_FORWARD
