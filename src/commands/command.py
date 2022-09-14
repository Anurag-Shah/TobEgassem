from abc import ABC

import discord


class Command(ABC):
    name: str
    description: str

    def run(self, msg: discord.Message):
        pass
