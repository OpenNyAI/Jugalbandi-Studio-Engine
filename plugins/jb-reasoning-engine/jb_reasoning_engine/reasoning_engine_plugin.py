from enum import Enum
from typing import Any, Dict, Optional
from jb_manager_bot import AbstractFSM
from jb_manager_bot.abstract_fsm import Variables
from jb_manager_bot.data_models import (
    Status,
)
from jb_manager_bot.parsers.utils import LLMManager


class ReturnStatus(Enum):
    SUCCESS = "success"
    BAD_REQUEST = "bad_request"
    UNAUTHORISED = "unauthorised"
    SERVER_ERROR = "server_error"


class PluginVariables(Variables):
    QUERY: Optional[str] = None
    SYSTEM_PROMPT: Optional[str] = None
    OPENAI_API_TYPE: Optional[str] = None
    OPENAI_API_ENDPOINT: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_VERSION: Optional[str] = None
    AZURE_CREDENTIAL_SCOPE: Optional[str] = None
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
    variable_names = PluginVariables
    return_status_values = ReturnStatus

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
        openai_api_type = getattr(self.variables, "OPENAI_API_TYPE")
        openai_api_key = getattr(self.variables, "OPENAI_API_KEY")
        openai_api_version = getattr(self.variables, "OPENAI_API_VERSION")
        openai_api_endpoint = getattr(self.variables, "OPENAI_API_ENDPOINT")
        azure_credential_scope = getattr(self.variables, "AZURE_CREDENTIAL_SCOPE")
        model = getattr(self.variables, "MODEL")

        llm_response = LLMManager.llm(
            messages=[
                LLMManager.sm(system_prompt),
                LLMManager.um(llm_query),
            ],
            model=model,
            openai_api_type=openai_api_type,
            openai_api_key=openai_api_key,
            openai_api_version=openai_api_version,
            openai_api_endpoint=openai_api_endpoint,
            azure_credential_scope=azure_credential_scope,
        )

        setattr(self.variables, "RESPONSE", llm_response)
        self.status = Status.MOVE_FORWARD
