import discord

from .command import Command
from .server import help

ALL_COMMANDS: list[Command] = [help]


class CommandHandler:
    commands: list[Command]

    def __init__(self, commands: list[Command]) -> None:
        self.commands = commands

    def handle_message(self, message: discord.Message) -> None:
        pass

    def handle_interaction(self, interaction: discord.Interaction) -> None:
        pass

    def help_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Tob (v1.0.0)",
            description=f"Tob will reverse 1 in {self.probability} messages.",
            color=0x4400DD,
        )
        for command in self.commands:
            embed.add_field(
                name=command.name,
                value=command.description,
                inline=False,
            )
        return embed


command_handler = CommandHandler(ALL_COMMANDS)
