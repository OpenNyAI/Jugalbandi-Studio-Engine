import base64
import json
import requests
import uuid
from enum import Enum
from typing import Any, Dict, Optional
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


def generate_auth_header(client_id: str, client_secret: str) -> str:
    auth_string = base64.b64encode(bytes(f"{client_id}:{client_secret}", "utf-8")).decode("utf-8")
    return f"Basic {auth_string}"

def request_payment(amount: int, client_id: str, client_secret: str, reference_id: str) -> str:
    url = "https://api.razorpay.com/v1/payment_links/"

    payload = json.dumps({"amount": amount * 100, "currency": "INR", "reference_id": reference_id})
    headers = {
        "Content-type": "application/json",
        "Authorization": generate_auth_header(client_id=client_id, client_secret=client_secret),
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response = json.loads(response.text)
    
    payment_url = response["short_url"]
    return payment_url


class paymentReturnStatus(Enum):
    SUCCESS = "success"
    CANCELLED_BY_USER = "cancelled_by_user"
    EXPIRED = "expired"
    SERVER_ERROR = "server_error"


class PaymentPluginVariables(Variables):
    MOBILE_NUMBER: Optional[str] = None
    NAME: Optional[str] = None
    CLIENT_ID: Optional[str] = None
    CLIENT_SECRET: Optional[str] = None
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
    variable_names = PaymentPluginVariables
    return_status_values = paymentReturnStatus

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
        client_id = getattr(self.variables, "CLIENT_ID")
        client_secret = getattr(self.variables, "CLIENT_SECRET")
        txn_id = str(uuid.uuid4())
        setattr(self.variables, "TXN_ID", txn_id)
        reference_id = self.get_reference_id()
        security_deposit_link = request_payment(amount, client_id=client_id, client_secret=client_secret, reference_id=reference_id)
        message_head = (
            f"To confirm your booking, please pay your deposit using the link: {security_deposit_link} \n"
            f"Security Deposit (held securely) Rs. {amount} \n"
            "Please pay the amount within 24 hours"
        )
        self.send_message(
            FSMOutput(
                intent=FSMIntent.SEND_MESSAGE,
                message=Message(
                    message_type=MessageType.TEXT, text=TextMessage(body=message_head)
                ),
            )
        )
        self.status = Status.WAIT_FOR_CALLBACK

    def on_enter_get_payment_status(self):
        self.status = Status.WAIT_FOR_ME
        payment_callback = json.loads(self.current_callback)
        payment_status = payment_callback["payload"]["order"]["entity"]["status"]
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
