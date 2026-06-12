import asyncio
from typing import Any

from dotenv import load_dotenv
import discord

from src.tob import AI_REQUEST_FAILED, Tob
from src.utils.utils import *
from src.utils.log import *

load_dotenv()


def get_message(content: str) -> discord.Message:
    class Message:
        def __init__(self, content: str) -> None:
            self.author = "author"
            self.guild = "guild"
            self.channel = "channel"
            self.content = content

        def reply(*a, **b) -> None:
            pass

    msg = Message(content)
    return msg


class TestTob:
    tob = Tob(twitter_tokens=env("TWITTER_TOKENS"), test=True, log_level=5)
    # Pre-populate cache to avoid hitting the Twitter API.
    tob.data["cache"]["is_twitter_video"]["1553120835686252544"] = False
    tob.data["cache"]["is_twitter_video"]["1553479370383171584"] = True

    def test_url_substitution(self):
        content = """Media discordapp net

    media.discordapp.net
    media.discordapp.net/bruhngus
    media.discordapp.net/bruhngus/bruhng
    media.discordapp.net/bruhngus/bruhng/us

    https://media.discordapp.net
    https://media.discordapp.net/bruhngus
    https://media.discordapp.net/bruhngus/bruhng
    https://media.discordapp.net/bruhngus/bruhng/us

    IMG

    twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ

    https://twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ

    <twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ>

    <https://twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ>

    VIDEO

    twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ

    https://twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ

    <twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ>

    <https://twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ>"""
        expected = "\n".join(
            [
                # "https://cdn.discordapp.com",
                # "https://cdn.discordapp.com/bruhngus",
                # "https://cdn.discordapp.com/bruhngus/bruhng",
                # "https://cdn.discordapp.com/bruhngus/bruhng/us",
                # "https://cdn.discordapp.com",
                # "https://cdn.discordapp.com/bruhngus",
                # "https://cdn.discordapp.com/bruhngus/bruhng",
                # "https://cdn.discordapp.com/bruhngus/bruhng/us",
                "https://vxtwitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ",
                "https://vxtwitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ",
            ]
        )

        msg = get_message(content)

        _, o = self.tob._handle_urlfix(msg, content)[0]
        assert o["content"] == expected

    def test_ai_query_accepts_whitespace_after_trigger(self):
        msg = get_message("@tob\nhello")

        assert self.tob._get_ai_query(msg, msg.content) == "hello"

    def test_ai_reply_retries_missing_content(self, monkeypatch):
        calls = 0

        async def request_ai_reply(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            if calls < 3:
                return None, True, None
            return "ok", False, None

        async def sleep(_delay):
            pass

        monkeypatch.setattr(self.tob, "_request_ai_reply", request_ai_reply)
        monkeypatch.setattr(asyncio, "sleep", sleep)
        self.tob.openai_web_search = False

        assert asyncio.run(self.tob._get_ai_reply("hello")) == "ok"
        assert calls == 3

    def test_ai_reply_falls_back_without_web_search(self):
        calls = []

        async def request_ai_reply(_session, _url, payload, _headers):
            calls.append("tools" in payload)
            if "tools" in payload:
                return None, False, None
            return "ok", False, None

        old_request_ai_reply = self.tob._request_ai_reply
        old_openai_web_search = self.tob.openai_web_search
        try:
            self.tob._request_ai_reply = request_ai_reply
            self.tob.openai_web_search = True

            assert asyncio.run(self.tob._get_ai_reply("source for hello")) == "ok"
            assert calls == [True, False]
        finally:
            self.tob._request_ai_reply = old_request_ai_reply
            self.tob.openai_web_search = old_openai_web_search

    def test_ai_web_search_only_for_search_queries(self):
        assert self.tob._should_use_web_search("source for hello")
        assert not self.tob._should_use_web_search("hello")

    def test_ai_reply_missing_choices_returns_error(self, monkeypatch):
        async def request_ai_reply(*_args, **_kwargs):
            return None, False, None

        monkeypatch.setattr(self.tob, "_request_ai_reply", request_ai_reply)
        self.tob.openai_web_search = False

        assert asyncio.run(self.tob._get_ai_reply("hello")) == AI_REQUEST_FAILED

    def test_ai_reply_truncates_discord_messages(self):
        reply = self.tob._format_discord_reply("x" * 2001)

        assert len(reply) == 2000
        assert reply.endswith("…")

    def test_reverse(self):
        assert fullreverse("hello world") == "dlrow olleh"
        assert fullreverse("real") == "laer"
        assert fullreverse("but it's a joke") == "ekoj a s'ti tub"

        # user
        assert fullreverse("<@132081113555402753>") == "<@132081113555402753>"
        # role
        assert fullreverse("<@&1019082056761876540>") == "<@&1019082056761876540>"
        # emote
        assert fullreverse("<:Clueless:910410243505283112>") == "<:Clueless:910410243505283112>"
        assert fullreverse("<:4C1:675444762333151232>") == "<:4C1:675444762333151232>"
        # time
        assert fullreverse("<")
        # delimits
        assert fullreverse("abc<@123>def<@456>ghi") == "ihg<@456>fed<@123>cba"
        # various negative tests
        assert fullreverse("<@123a>") == ">a321@<"
        assert fullreverse("<@123&456>") == ">654&321@<"
        assert fullreverse("<:qwert:y>") == ">y:trewq:<"
