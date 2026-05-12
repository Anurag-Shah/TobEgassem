import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

from src.tob import Tob


def _openrouter_key() -> str:
    if key := os.getenv("OPENROUTER_API_KEY"):
        return key
    return Path("~/.openrouter").expanduser().read_text().strip()


def _client(model: str = "openrouter/free", web_search: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        openai_api_key=_openrouter_key(),
        openai_base_url="https://openrouter.ai/api/v1",
        openai_model=model,
        openai_web_search=web_search,
    )


def _reply(prompt: str, model: str = "openrouter/free", web_search: bool = False) -> str:
    return asyncio.run(Tob._get_ai_reply(_client(model, web_search), prompt))


def test_openrouter_free_can_reply():
    assert _reply("Reply with exactly: tob ok") == "tob ok"


def test_openrouter_free_web_browsing_probe():
    reply = _reply(
        "What is the title of https://example.com/? Answer briefly and cite the source.",
        web_search=True,
    )
    print(reply)
    assert "Example Domain" in reply
