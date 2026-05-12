import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

from src.tob import Tob


def _openrouter_key() -> str:
    if key := os.getenv("OPENROUTER_API_KEY"):
        return key
    return Path("~/.openrouter").expanduser().read_text().strip()


def _client(model: str = "openrouter/free") -> SimpleNamespace:
    return SimpleNamespace(
        openai_api_key=_openrouter_key(),
        openai_base_url="https://openrouter.ai/api/v1",
        openai_model=model,
    )


def _reply(prompt: str, model: str = "openrouter/free") -> str:
    return asyncio.run(Tob._get_ai_reply(_client(model), prompt))


def test_openrouter_free_can_reply():
    assert _reply("Reply with exactly: tob ok") == "tob ok"


def test_openrouter_free_web_browsing_probe():
    reply = _reply(
        "Can you browse live web pages in this chat completion request? "
        "Answer with one short sentence."
    )
    print(reply)
    assert reply
