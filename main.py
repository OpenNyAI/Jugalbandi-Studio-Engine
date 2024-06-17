import os
import json
import time
import logging
import requests
import aiohttp
import asyncio
import multiprocessing
from base64 import b64decode
from dotenv import load_dotenv
from azure.storage.blob import BlobClient

from app.jb import JBEngine
from pwr_studio.kafka_utils import KafkaConsumer
from pwr_studio.types import Action, Response

# load_dotenv()

logger = logging.getLogger("jbengine")


async def main(msg: str) -> None:
    print(msg)
    start = time.time()
    if "blob_url" in msg:
        req = requests.get(msg["blob_url"], stream=True)
        content = b64decode(req.content).decode("utf-8")
        message = json.loads(content)
        blob_client = BlobClient.from_blob_url(msg["blob_url"])
        blob_client.delete_blob()
    else:
        message = msg
    correlation_id = message.get("correlation_id")
    logging.info(f"#2S - func.py Starting with {str(msg)}; PwR-RID={correlation_id}")

    action = Action.parse_obj(message)

    correlation_id = action.correlation_id
    response_url = action.response_url
    engine_name = action.engine_name

    logging.info(
        f"#2x - func.py Starting with {engine_name}:{action.action}; PwR-RID={correlation_id}"
    )

    response_url = action.response_url
    correlation_id = action.correlation_id
    session_id = action.session_id
    credentials = action.credentials

    credentials = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    }

    async def progress(data: Response):
        data.correlation_id = correlation_id
        data.session_id = session_id

        print("Sending response to: " + response_url)
        data = data.dict()
        print(data)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                response_url, json=data, headers={"content-type": "application/json"}
            ) as resp:
                logging.info(resp.status)
                content = await resp.text()

                # print(content)
                # print(resp.status)

                if resp.status != 200:
                    logging.info(
                        f"#2x - func.py JB Engine failed {resp.status}; PwR-RID={correlation_id}"
                    )
                    async with session.post(
                        response_url,
                        json=Response(
                            type="error",
                            message=f"JB Engine failed with status {resp.status}\n{content}",
                            correlation_id=correlation_id,
                            session_id=session_id,
                        ).dict(),
                    ) as r:
                        pass
                else:
                    logging.info(
                        f"#2x - func.py JB Engine succeeded; PwR-RID={correlation_id}"
                    )

    engine = JBEngine(action.project, progress, credentials=credentials)

    if action.action == "utterance":
        await engine.process_utterance(
            action.utterance, chat_history=action.chat_history, files=action.files
        )
    elif action.action == "representation_edit":
        await engine.process_representation_edit(action.changed_representation)
    elif action.action == "output":
        await engine.get_output(
            action.utterance, chat_history=action.chat_history, files=action.files
        )
    elif action.action == "import":
        await engine.process_import()
    elif action.action == "attachment":
        await engine.process_attachment()

    end = time.time()
    logging.info(
        f"#2E - func.py Completed in {end - start} seconds message in Q with {action}; PwR-RID={correlation_id}"
    )


async def main_invoker(queue):
    while True:
        try:
            msg = queue.get(block=True)
            if msg is not None:
                await main(msg)
        except Exception as e:
            import traceback

            print("Exception", e, traceback.format_exc())


def main_sync(queue) -> None:
    asyncio.run(main_invoker(queue))


NUM_PROCESSES = 4
kafka_broker = os.getenv("KAFKA_BROKER")
topic = os.getenv("KAFKA_ENGINE_TOPIC")
print(topic)
consumer = KafkaConsumer.from_env_vars(
    group_id="cooler_group_id", auto_offset_reset="latest"
)


def runner():
    msg_queue = multiprocessing.Queue()
    mpool = multiprocessing.Pool(NUM_PROCESSES, main_sync, (msg_queue,))

    while True:
        try:
            msg = consumer.receive_message(topic)
            logger.info("Received message %s", msg)
            msg = json.loads(msg)
            msg_queue.put(msg)
        except Exception as e:
            logger.error("Error %s", e)

    # prevent adding anything more to the queue and wait for queue to empty
    msg_queue.close()
    msg_queue.join_thread()

    # prevent adding anything more to the process pool and wait for all processes to finish
    mpool.close()
    mpool.join()


if __name__ == "__main__":
    runner()
