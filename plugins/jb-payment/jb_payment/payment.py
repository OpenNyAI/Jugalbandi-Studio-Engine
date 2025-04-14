import json
import uuid
from enum import Enum
from typing import Any, Dict, Optional
import urllib.parse
from jb_manager_bot import AbstractFSM
from jb_manager_bot.abstract_fsm import Variables
from jb_manager_bot.data_models import (
    FSMOutput,
    Status,
    FSMIntent,
    Message,
    MessageType,
    TextMessage,
)


def request_payment(
    mobile: str, reason: str, name: str, amount: int, payment_page_url: str
) -> str:
    query_params = {"amount": amount, "reason": reason, "mobile": mobile, "name": name}
    encoded_params = urllib.parse.urlencode(query_params)
    payment_url = f"{payment_page_url}?{encoded_params}"
    return payment_url


class ReturnStatus(Enum):
    SUCCESS = "success"
    CANCELLED_BY_USER = "cancelled_by_user"
    EXPIRED = "expired"
    SERVER_ERROR = "server_error"


class PluginVariables(Variables):
    MOBILE_NUMBER: Optional[str] = None
    NAME: Optional[str] = None
    PAYMENT_PAGE_URL: Optional[str] = None
    AMOUNT: Optional[float] = None
    REASON: Optional[str] = None
    TXN_ID: Optional[str] = None
    payment_status: Optional[str] = None


class payment(AbstractFSM):

    states = [
        "zero",
        "send_payment_request",
        "get_payment_status",
        "send_payment_success_confirmation",
        "send_payment_failed_confirmation",
        "end",
    ]
    transitions = [
        {
            "source": "get_payment_status",
            "dest": "send_payment_success_confirmation",
            "trigger": "next",
            "conditions": "is_payment_success",
        },
        {"source": "zero", "dest": "send_payment_request", "trigger": "next"},
        {
            "source": "send_payment_request",
            "dest": "get_payment_status",
            "trigger": "next",
        },
        {
            "source": "get_payment_status",
            "dest": "send_payment_failed_confirmation",
            "trigger": "next",
        },
        {
            "source": "send_payment_success_confirmation",
            "dest": "end",
            "trigger": "next",
        },
        {
            "source": "send_payment_failed_confirmation",
            "dest": "end",
            "trigger": "next",
        },
    ]
    conditions = {"is_payment_success"}
    output_variables = {"TXN_ID"}
    variable_names = PluginVariables
    return_status_values = ReturnStatus

    def __init__(self, send_message: callable, credentials: Dict[str, Any] = None):
        if credentials is None:
            credentials = {}

        self.credentials = credentials

        self.variables = self.variable_names()
        self.return_status_values = self.return_status_values.SUCCESS
        super().__init__(send_message)

    def on_enter_send_payment_request(self):
        self.status = Status.WAIT_FOR_ME
        amount = getattr(self.variables, "AMOUNT")
        mobile = getattr(self.variables, "MOBILE_NUMBER")
        name = getattr(self.variables, "NAME")
        reason = getattr(self.variables, "REASON")
        payment_page_url = getattr(self.variables, "PAYMENT_PAGE_URL")
        txn_id = str(uuid.uuid4())
        setattr(self.variables, "TXN_ID", txn_id)
        security_deposit_link = request_payment(
            payment_page_url=payment_page_url,
            amount=amount,
            mobile=mobile,
            reason=reason,
            name=name,
        )
        message_head = (
            "To confirm your booking, "
            f"please pay your deposit using the link: {security_deposit_link}"
            "\n"
            f"Security Deposit (held securely) {amount} INR \n"
            "Please pay the amount within 24 hours"
        )
        self.send_message(
            FSMOutput(
                intent=FSMIntent.SEND_MESSAGE,
                message=Message(
                    message_type=MessageType.TEXT, 
                    text=TextMessage(body=message_head)
                ),
            )
        )
        self.status = Status.WAIT_FOR_CALLBACK

    def on_enter_get_payment_status(self):
        self.status = Status.WAIT_FOR_ME
        payment_callback = json.loads(self.current_callback)
        payment_status = payment_callback["status"]
        setattr(
            self.variables,
            "payment_status",
            payment_status,
        )
        self.status = Status.MOVE_FORWARD

    def on_enter_send_payment_success_confirmation(self):
        self.status = Status.WAIT_FOR_ME
        self.return_status = self.return_status_values.SUCCESS
        self.send_message(
            FSMOutput(
                intent=FSMIntent.SEND_MESSAGE,
                message=Message(
                    message_type=MessageType.TEXT,
                    text=TextMessage(body="Payment Received!"),
                ),
            )
        )
        self.status = Status.MOVE_FORWARD

    def on_enter_send_payment_failed_confirmation(self):
        self.status = Status.WAIT_FOR_ME
        if self.variables.payment_status == "cancelled_by_user":
            self.return_status = self.return_status_values.CANCELLED_BY_USER
        elif self.variables.payment_status == "expired":
            self.return_status = self.return_status_values.EXPIRED
        else:
            self.return_status = self.return_status_values.SERVER_ERROR
        self.send_message(
            FSMOutput(
                intent=FSMIntent.SEND_MESSAGE,
                message=Message(
                    message_type=MessageType.TEXT,
                    text=TextMessage(body="Payment Failed!"),
                ),
            )
        )
        self.status = Status.MOVE_FORWARD

    def is_payment_success(self):
        return getattr(self.variables, "payment_status") == "paid"
