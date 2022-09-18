import asyncio
from typing import Any

import discord

from src.tob import Tob
from src.utils.utils import *
from src.utils.log import *


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
    tob = Tob(twitter_tokens=";;;;", test=True, log_level=5)

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

        (_, o) = self.tob._handle_urlfix(msg, content)[0]
        assert o["content"] == expected

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
