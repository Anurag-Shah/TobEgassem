from os.path import exists
import random
import re
import signal
import sys
from timeit import default_timer as timer
from typing import Any, Callable, TypedDict

from datetime import datetime
import discord

from utils.log import log
from utils.utils import *
from utils.font import fontify

# ------------------------------------------------------------------------------------------------ #
#                                          TobEgassem v3.0                                         #
# ------------------------------------------------------------------------------------------------ #

# ------------------------------------------- Constants ------------------------------------------ #

DATA_PATH = "data.json"

# replaces media.discordapp.net with cdn.discordapp.com for these extensions
DISCORD_VIDEO_EXTS = [".webm"]  # .mp4 and .mov work with media.discordapp.net

INIT_DATA = {
    "channels": [],
    "guilds": [],
    "blocked_channels": [],
    "cache": {"is_twitter_video": {}},
}

REACTION_IMGS = {
    "toolong": r"https://cdn.discordapp.com/attachments/441331703181475862/908667792000159795/IMG_0571.jpg",
    "essay": r"https://cdn.discordapp.com/attachments/638026953387147294/1262988669266952294/image.png?ex=6698995b&is=669747db&hm=3b7880224e522ee8502509be4af222b81605ded66317f868a1254038ff0d7ad6&",
    "busa": r"https://cdn.discordapp.com/attachments/441331703181475862/787027326901682206/me_waiting_busa.png",
    "funny": r"https://cdn.discordapp.com/attachments/441331703181475862/874813926834057266/video0.mp4",
    "kys": r"""💕         💕  💕          💕    💕💕💕
💕     💕         💕   💕    💕            💕
💕💕                   💕          💕
💕 💕                  💕                    💕
💕      💕             💕         💕            💕
💕         💕          💕             💕💕 💕""",
}

# ------------------------------------------- Patterns ------------------------------------------- #

# https://regexr.com/6r22i
TOB_REGEX = re.compile(r"(?:^|\W)tob(?:$|\W)", re.I | re.M)

# https://regexr.com/6r26d
URL_REGEX = re.compile(
    r"[(\<)?(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*(\>)?)",
    re.I | re.M,
)

# ---------------------------------------------- Tob --------------------------------------------- #


class Data(TypedDict):
    guilds: list[str]
    channels: list[str]
    blocked_channels: list[str]
    cache: dict[str, Any]


class InvalidCommandError(Exception):
    pass


class Tob(discord.Client):
    # TODO: Docsify this to __init__ (also these are not class variables)
    # Start time, to time ready seconds
    start_time: float
    # Twitter tokens in the following format: twitter_access_token;twitter_access_secret;twitter_consumer_key;twitter_consumer_secret
    api: tweepy.API
    # In how many messages will reverse a message
    probability: int
    # Replaces twitter.com when it's a Twitter video (because Discord default embeds suck)
    twitter_replacement: str
    # Run in test mode
    test: bool
    # Whether to reply to invalid command invocations
    reply_to_invalid_command: bool
    # Whether to clear cache on exit
    clear_cache: bool
    # Contains blocked channels, cache etc
    data: Any = INIT_DATA
    failed_loading_data: bool = False

    def __init__(
        self,
        twitter_tokens: str,
        log_level: int = 1,
        log_color: bool = False,
        probability: int = 69,
        twitter_replacement: str = "vxtwitter.com",
        test: bool = False,
        reply_to_invalid_command: bool = False,
        clear_cache: bool = False,
    ) -> None:
        intents = discord.Intents().default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.start_time = timer()
        self.api = get_tweepy_api_from_string(twitter_tokens)
        log.set_log_level(log_level)
        log.set_use_ansi_colors(log_color)
        self.probability = probability
        self.twitter_replacement = twitter_replacement
        self.test = test
        self.reply_to_invalid_command = reply_to_invalid_command
        self.clear_cache = clear_cache

        self._loadData()
        self._setSeed()

        if not self.test:
            # Register event handlers
            self.event(self.on_ready)
            self.event(self.on_message)
            signal.signal(signal.SIGINT, self._handle_ctrlc)  # type:ignore

    # -------------------------------------- Event Handlers -------------------------------------- #

    async def on_ready(self) -> None:
        elapsed = timer() - self.start_time
        log.info("Ready after:  {:.3f}s".format(elapsed), "on_ready")
        log.info(f"Logged in as: {self.user}", "on_ready")

    async def on_message(self, msg: discord.Message) -> None:
        # Dont respond to own messages or no message content
        if not self.test and (msg.author == self.user or not msg.content):
            return

        text: str = msg.content
        text_lower = text.lower()
        ch_id = str(msg.channel.id) if isinstance(msg.channel, object) else ""
        g_id = str(msg.guild.id) if isinstance(msg.guild, object) else ""

        log.trace(format_msg_full(msg), "on_message")

        try:
            # Bot commands
            # TODO: Variable prefix
            if text.startswith("|"):
                if await_responses := self._handle_command(msg, text, ch_id, g_id):
                    for x in await_responses:
                        await x[0](**x[1])
                return

            # Replace twitter.com and/or media.discordapp.net
            if "twitter.com" in text_lower or "media.discordapp.net" in text_lower:
                if await_responses := self._handle_urlfix(msg, text):
                    for x in await_responses:
                        await x[0](**x[1])

            # Replies with Sol's YouTube channel
            elif text_lower == "sub":
                log.debug(f"Sub: {format_msg_full(msg)}", "on_message::sub")
                await msg.reply(
                    "https://www.youtube.com/channel/UCptPtO9ndvMZhK_upk05wwg",
                    mention_author=False,
                )

            # Replies with bif bfrunbgussss!!!!
            elif text_lower in (
                "bif",
                "bruhngus",
                "bif bruhngus",
                "big bruhngus",
                "bfrunbgussss",
                "bif bfrunbgussss",
                "bif bfrunbgussss!!!!",
            ):
                log.debug("bif bfrunbgussss!!!!", "on_message::bif")
                await msg.reply(
                    "<:bif_bfrunbgussss_1:1002019180838670366><:bif_bfrunbgussss_2:1002019182394744873>\n<:bif_bfrunbgussss_3:1002019183548170291><:bif_bfrunbgussss_4:1002019184835842089>\n<:bif_bfrunbgussss_5:1002019186144444456><:bif_bfrunbgussss_6:1002019188149325906>",
                    mention_author=False,
                )

            # ain't reading all that, higher probability
            elif len(text_lower) > 1000:
                log.debug("ain't reading", "on_message::toolong")
                await msg.reply(
                    random.choices(
                        (REACTION_IMGS["toolong"], REACTION_IMGS["essay"]),
                        (3, 1)
                    )[0],
                    mention_author=False,
                )

            # Rolls 1 / self.probability and reverses the message
            elif self._valid_message(msg):
                if random_chance(self.probability):
                    log.debug(f"Reverse: {format_msg_full(msg)}", "on_message::reverse")
                    await msg.channel.send(fullreverse(text))

            # Reacts with specific text to certain keywords
            if len(re.findall(TOB_REGEX, text)) > 0:
                log.debug(f'React "Tob": {format_msg_full(msg)}', "on_message::react")
                await msg.add_reaction("❤")
            if text_lower == "like":
                log.debug(f'React "Like": {format_msg_full(msg)}', "on_message::react")
                await msg.add_reaction("👍")
            if text_lower == "f":
                log.debug(f'React "F": {format_msg_full(msg)}', "on_message::react")
                await msg.add_reaction("🇫")

        except (discord.Forbidden, discord.DiscordServerError) as e:
            log.warn(e, "on_message")
        except Exception as e:  # also discord.NotFound, discord.HTTPException
            log.error(e, "on_message")

    # TODO: Command framework
    def _handle_command(
        self, msg: discord.Message, text: str, ch_id: str, g_id: str
    ) -> list[tuple[Callable[[], Any], dict[str, Any]]]:
        commands = [x for x in text.lstrip("|").split(" |") if x]
        return_list: list[tuple[Callable[[], Any], dict[str, Any]]] = []
        try:
            for full_command in commands:
                args = [x for x in full_command.split()]
                if len(args) < 1:
                    raise InvalidCommandError()
                command = args[0].lower()
                subcommand = args[1].lower() if len(args) >= 2 else ""
                if command == "channel":
                    # TODO: Allow arbitrary IDs from input args
                    if subcommand == "add":
                        if self._add_channel(ch_id):
                            emb = discord.Embed(
                                title="Channel successfully added.",
                                description="Use `|channel remove` to undo this.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        else:
                            emb = discord.Embed(
                                title="Channel was added previously.",
                                description="Use `|channel remove` to remove it.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))

                    elif subcommand == "remove":
                        if self._remove_channel(ch_id):
                            emb = discord.Embed(
                                title="Channel was successfully removed.",
                                description="Use `|channel add` to undo this.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        else:
                            emb = discord.Embed(
                                title="Channel was removed previously.",
                                description="Use `|channel add` to add it.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))

                    elif subcommand == "status":
                        if ch_id in self.data["channels"]:
                            emb = discord.Embed(
                                title="Tob is enabled in this channel.",
                                description="Use `|channel remove` to disable it.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        elif ch_id in self.data["blocked_channels"]:
                            emb = discord.Embed(
                                title="Tob is disabled in this channel.",
                                description="Use `|channel add` to enable this.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        elif g_id in self.data["guilds"]:
                            emb = discord.Embed(
                                title="Tob is not enabled in this channel, but it is enabled server wide.",
                                description="Use `|channel add` to enable it explicitly.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        else:
                            emb = discord.Embed(
                                title="Tob is not enabled in this channel.",
                                description="Use `|channel add` to enable it.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))

                    else:
                        raise InvalidCommandError()

                elif command == "server":
                    if subcommand == "add":
                        if self._add_guild(g_id):
                            emb = discord.Embed(
                                title="Server successfully added.",
                                description="Use `|server remove` to undo this.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        else:
                            emb = discord.Embed(
                                title="Server was added previously.",
                                description="Use `|server remove` to remove it.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))

                    elif subcommand == "remove":
                        if self._remove_guild(g_id):
                            emb = discord.Embed(
                                title="Server successfully removed.",
                                description="Use `|server add` to undo this.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        else:
                            emb = discord.Embed(
                                title="Server was removed previously.",
                                description="Use `|server add` to add it.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))

                    elif subcommand == "status":
                        if g_id in self.data["guilds"]:
                            emb = discord.Embed(
                                title="Tob is enabled server-wide.",
                                description="Use `|server remove` to disable this.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))
                        else:
                            emb = discord.Embed(
                                title="Tob is not enabled server-wode.",
                                description="Use `|server add` to enable this.",
                                color=0x4400DD,
                            )
                            return_list.append((msg.reply, {"embed": emb, "mention_author": False}))

                    else:
                        raise InvalidCommandError()

                elif command == "help":
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
                    emb.add_field(
                        name="|channel remove",
                        value="Stops messages in current channel from being reversed, even if it is enabled for the entire server.",
                        inline=False,
                    )
                    emb.add_field(
                        name="|channel status",
                        value="Status of Tob in the current channel.",
                        inline=False,
                    )
                    emb.add_field(
                        name="|server add",
                        value="Allows all messages in this Server to be reversed.",
                        inline=False,
                    )
                    emb.add_field(
                        name="|server remove",
                        value="Stops messages in current server from being reversed (individual channels are unchanged).",
                        inline=False,
                    )
                    emb.add_field(
                        name="|server status",
                        value="Status of Tob in the current server.",
                        inline=False,
                    )
                    return_list.append((msg.reply, {"embed": emb, "mention_author": False}))

                elif command == "echo":
                    return_list.append(
                        (
                            msg.reply,
                            {
                                "content": full_command.split(" ", 1)[1].lstrip(),
                                "mention_author": False,
                            },
                        )
                    )

                elif command == "crphont":
                    return_list.append(
                        (
                            msg.reply,
                            {
                                "content": fontify(full_command.split(" ", 1)[1].lstrip()),
                                "mention_author": False,
                            },
                        )
                    )

                elif command in REACTION_IMGS:
                    return_list.append((msg.reply, {"content": REACTION_IMGS[command], "mention_author": False}))

                else:
                    raise InvalidCommandError()

        except InvalidCommandError:
            log.debug(
                f'Invalid commands: "{format_msg_full(msg)}"',
                "on_message::command",
            )
            self._handle_invalid_command(msg)
            return []
        else:
            log.debug(f'Commands: "{format_msg_full(msg)}"', "on_message::command")
            return return_list

    def _handle_urlfix(self, msg: discord.Message, text: str) -> list[tuple[Callable[[], Any], dict[str, Any]]]:
        log.debug(f"Replace: {format_msg_full(msg)}", "on_message::url")
        urls_replaced: list[str] = []
        _text = " ".join(text.split("\n"))
        iter = re.finditer(URL_REGEX, _text)
        for match in iter:
            url = match.group()

            # Skip urls that won't be embedded
            tokens = (url.startswith("<"), url.startswith(">"))
            if all(tokens):
                log.trace(f"Skipping <url>: {url}", "on_message::url")
                continue
            elif any(tokens):
                log.trace(f"Invalid <url>: {url}", "on_message::url")
                continue

            # Add https
            if not url.startswith("https://") and not url.startswith("http://"):
                url = "https://" + url

            # Replace twitter.com with self.twitter_replacement if it contains a video
            if "https://twitter.com" in url and self.twitter_replacement != "":
                replace_flag = False

                # Get Twitter Content ID from last part of URL
                url_id = url.split("/")[-1].split("?")[0]

                # Get media list from cache / Twitter API
                is_twitter_video = self.data["cache"]["is_twitter_video"].get(url_id)
                if is_twitter_video == True:
                    replace_flag = True
                # "not is_twitter_video" includes also False, which we want to skip since it has
                # been checked against the API already
                elif is_twitter_video == None:
                    entities = self.api.get_status(url_id).entities

                    if not "media" in entities:
                        self.data["cache"]["is_twitter_video"].update({url_id: False})
                        continue

                    media_list = entities["media"]

                    # Check if there's a video in the media list
                    for media_item in media_list:
                        if "video" in media_item["expanded_url"]:
                            replace_flag = True
                            self.data["cache"]["is_twitter_video"].update({url_id: True})
                            break
                    # Otherwise store False
                    if not replace_flag:
                        self.data["cache"]["is_twitter_video"].update({url_id: False})

                    self._save()

                # Replace and append to global list
                if replace_flag:
                    urls_replaced.append(url.replace("twitter.com", self.twitter_replacement))
            # Replace media.discordapp.net with cdn.discordapp.com because Discord moment
            elif "media.discordapp.net" in url and ends_with(url, DISCORD_VIDEO_EXTS):
                log.trace(
                    f"Replacing discord video with cdn: {url}",
                    "on_message::url",
                )
                urls_replaced.append(url.replace("media.discordapp.net", "cdn.discordapp.com"))

        # Reply if we replaced anything
        if len(urls_replaced) > 0:
            # Check if any of the URLs are missing https
            i = 0
            for url in urls_replaced:
                if not url.startswith("https://") and not url.startswith("http://"):
                    urls_replaced[i] = "https://" + url
                i += 1

            return [(msg.reply, {"content": "\n".join(urls_replaced), "mention_author": False})]
        return []

    def _handle_ctrlc(self, sig: signal.Signals, frame: Any) -> None:
        print()  # \n
        log.info("Received SIGINT, exiting...", "_handle_ctrlc")
        if self.clear_cache:
            self._clear_cache()
            log.info("Cleared cache", "_handle_ctrlc")
        sys.exit(0)

    # ------------------------------------------- Utils ------------------------------------------ #

    def _save(self) -> None:
        if not self.failed_loading_data:
            return writef(DATA_PATH, self.data)
        log.warn("Not writing to file since data was not properly loaded", "_save")

    def _clear_cache(self) -> None:
        try:
            self.data["cache"] = {}
        except:
            pass
        self._save()

    def _loadData(self) -> None:
        if exists(DATA_PATH):
            log.debug("Reading data from " + DATA_PATH, "_loadData")
            try:
                self.data = readf(DATA_PATH)
            except json.JSONDecodeError as e:
                log.error("Error decoding JSON:", "_loadData")
                log.error(f"{DATA_PATH}:{e.lineno} - {e.msg}", "_loadData")
                log.error("", "_loadData")
                self.failed_loading_data = True
            except Exception as e:
                log.error(f"{e}", "_loadData")
                self.failed_loading_data = True
        else:
            log.debug(DATA_PATH + " doesn't exist, creating a new file", "_loadData")
            writef(DATA_PATH, INIT_DATA)
        log.debug(f"Loaded data:  {self.data}", "_loadData")

    def _setSeed(self) -> None:
        seed = get_seed(self.data) + datetime.now().timestamp()
        log.debug(f"Loaded seed:  {seed}", "_setSeed")
        random.seed(seed)

    def _add_channel(self, channel_id: str) -> bool:
        if not isinstance(channel_id, str):
            channel_id = str(channel_id)
        ret = False
        if channel_id not in self.data["channels"]:
            ret = True
            self.data["channels"].append(channel_id)
        if channel_id in self.data["blocked_channels"]:
            self.data["blocked_channels"].remove(channel_id)
        self._save()
        return ret

    def _add_guild(self, guild_id: str) -> bool:
        if not isinstance(guild_id, str):
            guild_id = str(guild_id)
        ret = False
        if guild_id not in self.data["guilds"]:
            ret = True
            self.data["guilds"].append(guild_id)
        self._save()
        return ret

    def _remove_channel(self, channel_id: str) -> bool:
        if not isinstance(channel_id, str):
            channel_id = str(channel_id)
        ret = False
        if channel_id not in self.data["blocked_channels"]:
            ret = True
            self.data["blocked_channels"].append(channel_id)
        if channel_id in self.data["channels"]:
            self.data["channels"].remove(channel_id)
        self._save()
        return ret

    def _remove_guild(self, guild_id: str) -> bool:
        if not isinstance(guild_id, str):
            guild_id = str(guild_id)
        ret = False
        if guild_id in self.data["guilds"]:
            ret = True
            self.data["guilds"].remove(guild_id)
        self._save()
        return ret

    def _valid_message(self, msg: discord.Message) -> bool:
        ch_id = str(msg.channel.id)
        g_id = str(msg.guild.id) if msg.guild else ""
        return (ch_id not in self.data["blocked_channels"]) and (ch_id in self.data["channels"] or g_id in self.data["guilds"])

    # TODO
    def _handle_invalid_command(self, msg: discord.Message) -> None:
        if not self.reply_to_invalid_command:
            return

        log.warn("Not implemented", "tob::_handle_invalid_command")
        return

        embed = discord.Embed(
            title="Channel successfully added.",
            description="Use `|channel remove` to undo this.",
            color=0x4400DD,
        )
        msg.reply(embed=embed, mention_author=False)
