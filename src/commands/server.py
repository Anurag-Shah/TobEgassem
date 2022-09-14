import discord

from .command import Command


class Help(Command):
    name: str = "help"
    description: str = "Replies with this help message"

    def run(self, msg: discord.Message):
        emb = discord.Embed(
            title="Tob (v1.0.0)",
            description=f"Tob will reverse 1 in {self.probability} messages.",
            color=0x4400DD,
        )
        emb.add_field(
            name="|channel add",
            value="Allows messages in the current channel to be reversed.",
            inline=False,
        )


help = Help()
