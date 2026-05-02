# client.py
#
# Purpose: OpenAI client initialization and API calling
#
# This module:
# - Manages the shared OpenAI client instance
# - Handles raw API calls with timeout and await indicator
# - Supports tool-calling variant for structured responses

import os

from openai import OpenAI

from ..ui import AwaitIndicator, TIMEOUT

_client = None


def init_client(config):
    global _client
    _client = OpenAI(api_key=config.api_key, base_url=config.base_url)


def reinit_client(config):
    global _client
    _client = OpenAI(api_key=config.api_key, base_url=config.base_url)


def _call_api(messages, max_tokens=256):
    with AwaitIndicator():
        response = _client.chat.completions.create(
            model=os.environ["NLSH_MODEL"],
            messages=messages,
            max_tokens=max_tokens,
            timeout=TIMEOUT,
        )
    return response.choices[0].message.content.strip()


def _call_api_tools(messages, tools, max_tokens=256):
    with AwaitIndicator():
        response = _client.chat.completions.create(
            model=os.environ["NLSH_MODEL"],
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=max_tokens,
            timeout=TIMEOUT,
        )
    return response.choices[0].message
