import asyncio
import os
from enum import Enum
from pathlib import Path

import chainlit as cl

from chainlit.input_widget import Slider, Switch

from strands.models import BedrockModel
from strands_tools import http_request, speak

from strands_utils import get_response

USERNAME = "strands-agents"
PASSWORD = "pwd4strands"
if os.getenv("USERNAME") and os.getenv("PASSWORD"):
    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")

MODEL_TEMPERATURE = "model temperature"
MAX_TOKENS = "max tokens"
PROGRESS_MESSAGES = "progress messages"
TOP_P = "top_p"
MP3_FILE = "mp3 file"
SVG_IMAGE = "svg image"

CHAT_SETTINGS = [MODEL_TEMPERATURE, MAX_TOKENS, PROGRESS_MESSAGES, TOP_P, MP3_FILE, SVG_IMAGE]


class ModelName(Enum):
    NOVA_PREMIER = "Amazon Nova Premier"
    SONNET_V4 = "Claude Sonnet v4"
    SONNET_V3_7 = "Claude Sonnet v3.7"
    LLAMA_MAVERICK_V4 = "Llama Maverick v4"
    DEEPSEEK_R1 = "DeepSeek R1"


class BedrockLLM(Enum):
    NOVA_PREMIER = "us.amazon.nova-premier-v1:0"
    SONNET_V4 = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    SONNET_V3_7 = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    LLAMA_MAVERICK_V4 = "us.meta.llama4-maverick-17b-instruct-v1:0"
    DEEPSEEK_R1 = "us.deepseek.r1-v1:0"


STEP_DURATION: int = 3

MP3_GENERATION: bool = True
SVG_GENERATION: bool = True
MSG_GENERATION: bool = True

FILE_DIR = "/tmp"
WEATHER_MP3 = "weather.mp3"
WEATHER_SVG = "weather.svg"

# Define a weather-focused system prompt
WEATHER_SYSTEM_PROMPT = """
You are a weather assistant with HTTP capabilities. 

You can:
1. Make HTTP requests to the National Weather Service API
2. Process and display weather forecast data
3. Provide weather information for locations in the United States

When retrieving weather information:
1. First get the coordinates or grid information using https://api.weather.gov/points/{{latitude}},{{longitude}} 
or https://api.weather.gov/points/{{zipcode}}
2. Then use the returned forecast URL to get the actual forecast

When displaying responses:
- Format weather data in a human-readable way
- Highlight important information like temperature, precipitation, and alerts
- Handle errors appropriately
- Convert technical terms to user-friendly language

Always explain the weather conditions clearly and provide context for the forecast.
"""

SPEAK_PROMPT = f"""
can you generate an mp3 sound file named '{WEATHER_MP3}' speaking the weather forecast that you already generated ?
Place it in directory {FILE_DIR})
"""

CHART_SYSTEM_PROMPT = """
You are a graphical design assistant with capabilities to generate SVG charts. 

You can:
1. Analyse data provided as input
2. Structure this data in order to generate a chart picturing this data with info regarding x-axis and y-axis 
3. Generate the SVG chart in your response 


When displaying responses:
- Start the SVG chart with tag ```
- Only return SVG data. Do NOT add any words or comments describing the results.
"""

CHART_PROMPT = """
generate SVG chart for temperature and precipitation with the response that you already returned
"""


@cl.on_message
async def on_message(message: cl.Message):
    from strands import Agent # pylint: disable=C0415

    chat_settings = cl.user_session.get("chat_settings")
    for key in chat_settings.keys():
        assert key in CHAT_SETTINGS
    model_name = cl.user_session.get("chat_profile")
    match model_name:  # noqa
        case ModelName.NOVA_PREMIER.value:
            model_id = BedrockLLM.NOVA_PREMIER.value
        case ModelName.SONNET_V4.value:
            model_id = BedrockLLM.SONNET_V4.value
        case ModelName.SONNET_V3_7.value:
            model_id = BedrockLLM.SONNET_V3_7.value
        case ModelName.LLAMA_MAVERICK_V4.value:
            model_id = BedrockLLM.LLAMA_MAVERICK_V4.value
        case ModelName.DEEPSEEK_R1.value:
            model_id = BedrockLLM.DEEPSEEK_R1.value
        case _:
            raise ValueError(f"Unknown LLM: {model_name}")
    weather_agent = Agent(
        system_prompt=WEATHER_SYSTEM_PROMPT,
        tools=[http_request, speak],
        # https://github.com/strands-agents/samples/blob/main/02-samples/01-restaurant-assistant/restaurant-assistant.ipynb
        model=BedrockModel(
            model_id=model_id,
            temperature=chat_settings[MODEL_TEMPERATURE],
            max_tokens=int(chat_settings[MAX_TOKENS]),
            top_p=chat_settings[TOP_P],
            # region_name="us-east-1",
        )
    )
    print(f"agent model: {weather_agent.model.config}")
    question = f"{message.content}"
    response = await get_response(agent=weather_agent,
                                  prompt=question,
                                  step=STEP_DURATION,
                                  progress_messages=chat_settings[PROGRESS_MESSAGES])
    await cl.Message(
        content=f"Request (id: {message.id}): {message.content} \n {response}",
    ).send()
    if chat_settings[MP3_FILE]:
        await produce_mp3(weather_agent)
    if chat_settings[SVG_IMAGE]:
        await produce_svg(weather_agent)


async def produce_mp3(agent):
    if Path(FILE_DIR,WEATHER_MP3).is_file():
        Path(FILE_DIR,WEATHER_MP3).unlink()
    await cl.Message(
        content="Preparing MP3 audio weather forecast with Amazon Polly...",
    ).send()
    await get_response(agent=agent, prompt=SPEAK_PROMPT, step=STEP_DURATION)
    while not Path(FILE_DIR,WEATHER_MP3).is_file():
        await asyncio.sleep(0.2)
    elements = [
        cl.Audio(name=f"{WEATHER_MP3}", path=str(Path(FILE_DIR,WEATHER_MP3)), display="inline"),
    ]
    await cl.Message(
        content="Delivering MP3 audio weather forecast...",
        elements=elements,
    ).send()


async def produce_svg(agent):
    await cl.Message(
        content="Preparing chart for weather forecast...",
    ).send()
    # System prompt is adapted to chart generation before query to improve results.
    prompt_backup = agent.system_prompt
    agent.system_prompt = CHART_SYSTEM_PROMPT
    request = "generate SVG chart for temperature and precipitation with the response that you already returned"
    image_content: str = await get_response(agent=agent, prompt=request, step=STEP_DURATION)
    image_content = image_content.split("```")[1]  # image content in between pair of 3 backticks
    image_content = image_content.strip("\n")
    print(f"image content: {image_content}")
    svg_path = Path(FILE_DIR, WEATHER_SVG)
    svg_path.write_text(image_content, encoding="utf-8")
    image = cl.Image(path=str(svg_path), mime="image/svg+xml", size="large", name="image1", display="inline")
    await cl.Message(
        content="chart for weather forecast",
        elements=[image],
    ).send()
    agent.system_prompt = prompt_backup


@cl.set_chat_profiles
async def set_chat_profile():
    return [
        cl.ChatProfile(
            name=ModelName.SONNET_V3_7.value,
            markdown_description=f"Strands Agent - Weather forecast with **{ModelName.SONNET_V3_7.value}**.",
            icon="https://picsum.photos/60",
        ),
        cl.ChatProfile(
            name=ModelName.NOVA_PREMIER.value,
            markdown_description=f"Strands Agent - Weather forecast with **{ModelName.NOVA_PREMIER.value}**.",
            icon="https://picsum.photos/40",
        ),
        cl.ChatProfile(
            name=ModelName.SONNET_V4.value,
            markdown_description=f"Strands Agent - Weather forecast with **{ModelName.SONNET_V4.value}**.",
            icon="https://picsum.photos/50",
        ),
        cl.ChatProfile(
            name=ModelName.LLAMA_MAVERICK_V4.value,
            markdown_description=f"Strands Agent - Weather forecast with **{ModelName.LLAMA_MAVERICK_V4.value}**.",
            icon="https://picsum.photos/70",
        ),
        cl.ChatProfile(
            name=ModelName.DEEPSEEK_R1.value,
            markdown_description=f"Strands Agent - Weather forecast **{ModelName.DEEPSEEK_R1.value}**.",
            icon="https://picsum.photos/80",
        ),
    ]


@cl.on_chat_start
async def on_chat_start():
    chat_profile = cl.user_session.get("chat_profile")
    await cl.Message(
        content=f"starting chat using the {chat_profile} chat profile"
    ).send()


@cl.on_chat_start
async def on_chat_start2():
    await cl.ChatSettings(
        [
            Slider(
                id=MODEL_TEMPERATURE,
                label=MODEL_TEMPERATURE,
                initial=0,
                min=0,
                max=1,
                step=0.1,
            ),
            Slider(
                id=MAX_TOKENS,
                label=MAX_TOKENS,
                initial=20_000,
                min=0,
                max=40_000,
                step=5_000,
            ),
            Slider(
                id=TOP_P,
                label=TOP_P,
                initial=0.3,
                min=0.0,
                max=1.0,
                step=0.1,
            ),
            Switch(
                id=PROGRESS_MESSAGES,
                label=PROGRESS_MESSAGES,
                initial=MSG_GENERATION,
            ),
            Switch(
                id=MP3_FILE,
                label=MP3_FILE,
                initial=MP3_GENERATION,
            ),
            Switch(
                id=SVG_IMAGE,
                label=SVG_IMAGE,
                initial=SVG_GENERATION,
            ),
        ]
    ).send()


@cl.on_settings_update
async def on_settings_update(settings):
    print("on_settings_update", settings)


@cl.password_auth_callback
def password_auth_callback(username: str, password: str):
    print(f"auth callback: {username} / {password}")
    if (username, password) == (USERNAME, PASSWORD):
        print(f"authenticated user: {username} ")
        return cl.User(
            identifier=username
        )
    return None
