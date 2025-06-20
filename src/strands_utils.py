import logging
import os
import shutil
import time
from enum import Enum
from os.path import isfile, isdir
from pathlib import Path

from pydantic import BaseModel
from starlette.applications import Starlette

from fastapi import FastAPI
from strands_tools import speak, http_request

from constants import SRC_PATH, STRANDS_HTTP_PORT

logger = logging.getLogger(__name__)


class StrandsTool(Enum):
    HTTP_REQUEST = "request"
    SPEAK = "speak"


ROLE = "role"
USER = "user"
ASSISTANT = "assistant"
CONTENT = "content"
TEXT = "text"

EVENT_LOOP_METRICS = "event_loop_metrics"
ACCUMULATED_USAGE = "accumulated_usage"
INPUT_TOKENS = "inputTokens"
OUTPUT_TOKENS = "outputTokens"
TOTAL_TOKENS = "totalTokens"


# see https://strandsagents.com/0.1.x/user-guide/concepts/streaming/async-iterators/
class EventType(Enum):
    # Lifecycle events:
    INIT_EVENT_LOOP = "init_event_loop"
    START_EVENT_LOOP = "start_event_loop"
    START = "start"
    EVENT = "event"
    MESSAGE = "message"
    FORCE_STOP = "force_stop"
    FORCE_STOP_REASON = "force_stop_reason"
    # Text generation events
    DATA = "data"
    COMPLETE = "complete"
    DELTA = "delta"
    # Tool events
    CURRENT_TOOL_USE = "current_tool_use"
    # Reasoning events
    REASONING = "reasoning"
    REASONING_TEXT = "reasoningText"
    REASONING_SIGNATURE = "reasoning_signature"

class BedrockModel(BaseModel):
    model_id: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None

class AgentParameters(BaseModel):
    system_prompt: str | None = None
    tools: list[StrandsTool] | None = None
    model: BedrockModel | None = None

class AgentConfig(BaseModel):
    echo: bool = False
    id: str | None = None
    agent_parameters: AgentParameters | None = None

class AgentInstance(BaseModel):
    model: BedrockModel | None = None
    system_prompt: str | None = None
    tools: list[StrandsTool] | None = None


def check_event(event) -> list[EventType] | None:
    # print(f": event type: {type(event)}")
    assert isinstance(event, dict)
    result = list[EventType]()
    not_found: bool = True
    for event_type in EventType:
        if event_type.value in event:
            if not_found:
                not_found = False
            result.append(event_type)
    if not_found:
        raise ValueError(f"unknown event type ({type(event)}): {event}")
    if len(result) == 0:
        return None
    return result


async def get_response(agent=None, prompt: str = "", step: int = -1, progress_messages: bool = False) -> str:
    from strands.telemetry import EventLoopMetrics  # pylint: disable=C0415

    message = None
    start_time = time.time()
    last_time = time.time()
    async for event in agent.stream_async(prompt=prompt):
        if progress_messages:
            if step > 0 and time.time() >= last_time + step:
                content = f"still working after {time.time() - start_time:.1f}s... "
                if EVENT_LOOP_METRICS in event:
                    last_time = time.time()  # reset only when we can publish usage stats
                    # print(f"USAGE_METRICS: {event}")
                    assert isinstance(event[EVENT_LOOP_METRICS], EventLoopMetrics)
                    input_tokens = event[EVENT_LOOP_METRICS].accumulated_usage[INPUT_TOKENS]
                    output_tokens = event[EVENT_LOOP_METRICS].accumulated_usage[OUTPUT_TOKENS]
                    total_tokens = event[EVENT_LOOP_METRICS].accumulated_usage[TOTAL_TOKENS]
                    content += (f"(accumulated usage: input tokens: {input_tokens:,} "
                                f"- output tokens: {output_tokens:,} "
                                f"- total tokens: {total_tokens:,})")
                    # just-in-time import to avoid "wild" dir creations by imported app before configure_chainlit()
                    import chainlit as cl  # pylint: disable=C0415
                    await cl.Message(
                        content=content,
                    ).send()
        check_event(event)
        if EventType.MESSAGE.value in event:
            if ROLE in event[EventType.MESSAGE.value]:
                if event[EventType.MESSAGE.value][ROLE] == ASSISTANT:
                    message = event[EventType.MESSAGE.value]
                else:
                    assert event[EventType.MESSAGE.value][ROLE] == USER  # just to make sure that only 2 roles exist
            else:
                raise ValueError(f"no role in event: {event}")
    print(message)
    assert message[ROLE] == ASSISTANT
    return message[CONTENT][0][TEXT]


def configure_chainlit():
    chainlit_path = Path(os.getenv("CHAINLIT_APP_ROOT"), ".chainlit")
    if not isdir(chainlit_path):
        print(f"configuring chainlit with path: {chainlit_path}")
        shutil.copytree(Path(SRC_PATH, ".chainlit"), chainlit_path)
        assert isfile(Path(chainlit_path, "config.toml"))


def setup_chainlit(root_path: str = "",
                   target_script: str = "",
                   http_host: str = "0.0.0.0",
                   http_port: int = STRANDS_HTTP_PORT):

    configure_chainlit()

    # just-in-time import to avoid "wild" dir creations by imported app before configure_chainlit()
    from chainlit.config import config, load_module  # pylint: disable=C0415

    config.run.headless = True
    config.run.debug = os.environ.get("CHAINLIT_DEBUG", False)
    config.run.host = http_host
    config.run.port = http_port
    config.run.root_path = root_path

    # must come after config definition
    from chainlit.server import app as chainlit_app  # pylint: disable=C0415
    from chainlit.auth import ensure_jwt_secret  # noqa pylint: disable=C0415
    from chainlit.utils import check_file  # pylint: disable=C0415

    check_file(target_script)
    config.run.module_name = target_script
    load_module(config.run.module_name)
    ensure_jwt_secret()

    # @chainlit_app.get("/request")
    # def publish_request(request: Request):
    #     return {REQUEST: request_as_dict(request)}

    return chainlit_app


def mount_chainlit(app: FastAPI | Starlette | None = None, target_script: str = "", url_path: str = ""):
    # just-in-time import to avoid "wild" dir creations by imported app before configure_chainlit()
    from chainlit.server import app as chainlit_app  # pylint: disable=C0415
    from chainlit.config import config, load_module  # pylint: disable=C0415
    from chainlit.auth import ensure_jwt_secret  # noqa pylint: disable=C0415
    from chainlit.utils import check_file  # pylint: disable=C0415

    config.run.debug = os.environ.get("CHAINLIT_DEBUG", False)
    os.environ["CHAINLIT_ROOT_PATH"] = url_path
    if hasattr(app, "root_path"):
        os.environ["CHAINLIT_PARENT_ROOT_PATH"] = app.root_path.rstrip("/")
    check_file(target_script)
    config.run.module_name = target_script
    load_module(config.run.module_name)
    ensure_jwt_secret()
    app.mount(url_path, chainlit_app)
    if not url_path.endswith("/"):
        app.mount(url_path + "/", chainlit_app)
    else:
        app.mount(url_path[:-1], chainlit_app)


def tool_map(tool: StrandsTool):
    if tool == StrandsTool.SPEAK:
        return speak
    if tool == StrandsTool.HTTP_REQUEST:
        return http_request
    raise ValueError(f"unknown tool: {tool}")
