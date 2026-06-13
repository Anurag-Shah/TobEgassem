import asyncio
import os
from pathlib import Path
import pytest

from src.tob import Tob

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_OPENROUTER_TESTS"),
    reason="set RUN_OPENROUTER_TESTS=1 to run OpenRouter integration tests",
)


def _openrouter_key() -> str:
    if key := os.getenv("OPENROUTER_API_KEY"):
        return key
    path = Path("~/.openrouter").expanduser()
    if path.exists():
        return path.read_text().strip()
    pytest.skip("OPENROUTER_API_KEY or ~/.openrouter is required")


def _client(model: str = "openai/gpt-5-nano", web_search: bool = False) -> Tob:
    return Tob(
        twitter_tokens=os.getenv("TWITTER_TOKENS", "a;b;c;d"),
        test=True,
        openai_api_key=_openrouter_key(),
        openai_base_url="https://openrouter.ai/api/v1",
        openai_model=model,
        openai_web_search=web_search,
    )


def _reply(prompt: str, model: str = "openai/gpt-5-nano", web_search: bool = False) -> str:
    return asyncio.run(Tob._get_ai_reply(_client(model, web_search), prompt))


def test_openrouter_can_reply():
    assert _reply("Reply with exactly: tob ok") == "tob ok"


def test_openrouter_web_browsing_probe():
    reply = _reply(
        "What is the title of https://example.com/? Answer briefly and cite the source.",
        web_search=True,
    )
    print(reply)
    assert "Example Domain" in reply
