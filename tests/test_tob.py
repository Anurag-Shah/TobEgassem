import asyncio
from typing import Any

from dotenv import load_dotenv
import discord

from src.tob import AI_REQUEST_FAILED, DISCORD_MESSAGE_MAX_LENGTH, Tob
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
                return None, None
            return "ok", None

        async def sleep(_delay):
            pass

        monkeypatch.setattr(self.tob, "_request_ai_reply", request_ai_reply)
        monkeypatch.setattr(asyncio, "sleep", sleep)
        self.tob.openai_web_search = False

        assert asyncio.run(self.tob._get_ai_reply("hello")) == "ok"
        assert calls == 3

    def test_ai_reply_always_passes_web_search_capability(self):
        payloads = []

        async def request_ai_reply(_session, _url, payload, _headers):
            payloads.append(payload)
            return "ok", None

        old_request_ai_reply = self.tob._request_ai_reply
        old_openai_web_search = self.tob.openai_web_search
        try:
            self.tob._request_ai_reply = request_ai_reply
            self.tob.openai_web_search = True

            assert asyncio.run(self.tob._get_ai_reply("hello")) == "ok"
            assert payloads
            assert all("tools" in payload for payload in payloads)
        finally:
            self.tob._request_ai_reply = old_request_ai_reply
            self.tob.openai_web_search = old_openai_web_search

    def test_ai_reply_missing_choices_returns_error(self, monkeypatch):
        async def request_ai_reply(*_args, **_kwargs):
            return None, None

        monkeypatch.setattr(self.tob, "_request_ai_reply", request_ai_reply)
        self.tob.openai_web_search = False

        assert asyncio.run(self.tob._get_ai_reply("hello")) == AI_REQUEST_FAILED

    def test_split_discord_reply_prefers_word_boundaries(self):
        reply = "x" * 1999 + " " + "hello"
        chunks = self.tob._split_discord_reply(reply)

        assert chunks == ["x" * 1999, "hello"]
        assert all(len(chunk) <= DISCORD_MESSAGE_MAX_LENGTH for chunk in chunks)

    def test_split_discord_reply_splits_long_words(self):
        chunks = self.tob._split_discord_reply("x" * 2001)

        assert chunks == ["x" * 2000, "x"]
        assert all(len(chunk) <= DISCORD_MESSAGE_MAX_LENGTH for chunk in chunks)

    def test_send_discord_reply_chain_replies_to_previous_message(self):
        class Message:
            messages = []

            def __init__(self, content=""):
                self.content = content
                self.replies = []

            async def reply(self, content, mention_author):
                reply = Message(content)
                self.replies.append((reply, mention_author))
                Message.messages.append(reply)
                return reply

        msg = Message()
        chunks = ["first", "second", "third"]
        old_split_discord_reply = self.tob._split_discord_reply
        try:
            self.tob._split_discord_reply = lambda _reply: chunks
            replies = asyncio.run(self.tob._send_discord_reply_chain(msg, "ignored"))
        finally:
            self.tob._split_discord_reply = old_split_discord_reply

        assert replies == Message.messages
        assert [reply.content for reply in replies] == chunks
        assert msg.replies == [(replies[0], True)]
        assert replies[0].replies == [(replies[1], False)]
        assert replies[1].replies == [(replies[2], False)]

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
