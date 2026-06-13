from os.path import exists
import asyncio
from dataclasses import dataclass
import html
import json
import random
import re
import signal
import sys
from timeit import default_timer as timer
from typing import Any, Callable, TypedDict

from datetime import datetime, timezone
import aiohttp
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

AI_TRIGGER = "@tob "
AI_ADMIN_USER_IDS = {302516756256391168}
AI_CONTEXT_MAX_AGE_SECONDS = 60 * 60
AI_CONTEXT_MAX_MESSAGES = 50
AI_REQUEST_FAILED = "AI request failed."
AI_REQUEST_MAX_ATTEMPTS = 3
AI_REQUEST_TIMEOUT_SECONDS = 45
AI_RETRY_DELAY_SECONDS = 1
AI_RETRY_MAX_DELAY_SECONDS = 15
DISCORD_MESSAGE_MAX_LENGTH = 2000
AI_SYSTEM_PROMPT = """
you're tob, a friendly ai chatbot embedded in a discord server.

tob behavior:
- your main bit is occasionally reversing messages with low probability
- you also do some simple message reactions and commands
- never reverse messages yourself, the harness handles that when needed
- if context says the harness will reverse output, still write a normal unreversed reply

reply similarly to the messages in the provided context:
- match their tone, length, formality, punctuation, and casual group-chat rhythm
- ignore context if it's not relevant to the request
- context may include previous conversation between the query author and you
- always use lowercase
- keep it short unless someone clearly asks for detail
- never use em dashes
- never talk like an ai, assistant, customer support bot, essay writer, or brand account
- don't force slang, memes, jokes, or fake personality
- no cringe shit
- be useful and direct for books, anime, sports, gardening, politics, language, memes, and links
- if you use web search, cite sources briefly

format discord messages correctly when needed:
- user mention: <@user_id>
- channel mention: <#channel_id>
- role mention: <@&role_id>
- custom emoji: <:name:emoji_id> or <a:name:emoji_id> for animated emoji
- timestamp: <t:unix_timestamp> or <t:unix_timestamp:style>, styles include t, T, d, D, f, F, R
- spoiler text: ||spoiler||
- basic markdown works: **bold**, *italic*, __underline__, `code`, ```code block```, > quote
- don't use @everyone, @here, or role pings unless explicitly asked
- use ids from context if you need to mention a specific user or channel

- don't pretend to know private server lore beyond the current message
- don't repeat slurs or hateful phrasing
""".strip()

# ---------------------------------------------- Tob --------------------------------------------- #


class Data(TypedDict):
    guilds: list[str]
    channels: list[str]
    blocked_channels: list[str]
    cache: dict[str, Any]


class InvalidCommandError(Exception):
    pass


@dataclass
class AiContextMessage:
    created_at: float
    channel_id: str
    message_id: int
    author_key: str
    display_name: str
    author_extra: str
    content: str


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
    # OpenAI-compatible API settings
    enable_ai: bool
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    openai_web_search: bool
    # Contains blocked channels, cache etc
    data: Any = INIT_DATA
    failed_loading_data: bool = False
    ai_message_context: list[AiContextMessage]
    active_messages: int
    shutting_down: bool
    shutdown_waiter: asyncio.Event | None

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
        enable_ai: bool = False,
        openai_api_key: str | None = None,
        openai_base_url: str = "https://api.openai.com/v1",
        openai_model: str = "gpt-4o-mini",
        openai_web_search: bool = False,
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
        self.enable_ai = enable_ai
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url.rstrip("/")
        self.openai_model = openai_model
        self.openai_web_search = openai_web_search
        self.ai_message_context = []
        self.active_messages = 0
        self.shutting_down = False
        self.shutdown_waiter = None

        self._loadData()
        self._setSeed()

        if not self.test:
            # Register event handlers
            self.event(self.on_ready)
            self.event(self.on_message)
            self.event(self.on_message_edit)
            self.event(self.on_raw_message_delete)
            self.event(self.on_raw_bulk_message_delete)
            signal.signal(signal.SIGINT, self._handle_ctrlc)  # type: ignore

    # -------------------------------------- Event Handlers -------------------------------------- #

    async def on_ready(self) -> None:
        elapsed = timer() - self.start_time
        log.info("Ready after:  {:.3f}s".format(elapsed), "on_ready")
        log.info(f"Logged in as: {self.user}", "on_ready")

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not after.content:
            self._remove_ai_context_message(after.id)
            return
        self._update_ai_context_message(after, after.content)

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        self._remove_ai_context_message(payload.message_id)

    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent) -> None:
        self._remove_ai_context_messages(payload.message_ids)

    async def on_message(self, msg: discord.Message) -> None:
        # Dont respond to no message content
        if not self.test and not msg.content:
            return
        if self.shutting_down:
            return

        text: str = msg.content
        text_lower = text.lower()
        ch_id = str(msg.channel.id) if isinstance(msg.channel, object) else ""
        g_id = str(msg.guild.id) if isinstance(msg.guild, object) else ""

        log.trace(format_msg_full(msg), "on_message")
        if not self.test and msg.author == self.user:
            self._record_ai_context(msg, text, ch_id)
            return

        self.active_messages += 1
        try:
            # AI chat
            if query := self._get_ai_query(msg, text):
                if query.lower() in ("ai enable", "ai disable"):
                    if not self._is_admin(msg):
                        log.debug("Ignoring AI command from non-admin", "on_message::ai")
                        return
                    if query.lower() == "ai enable" and not self.openai_api_key:
                        log.debug(
                            "Ignoring AI enable command because OPENAI_API_KEY is not set",
                            "on_message::ai",
                        )
                        return
                    self.enable_ai = query.lower() == "ai enable"
                    await msg.reply(
                        f"ai {'enabled' if self.enable_ai else 'disabled'}", mention_author=True
                    )
                    return

                if not self.enable_ai:
                    log.debug("Ignoring AI prompt because AI is disabled", "on_message::ai")
                    return
                if not self.openai_api_key:
                    log.debug(
                        "Ignoring AI prompt because OPENAI_API_KEY is not set", "on_message::ai"
                    )
                    return

                log.debug(f"AI: {format_msg_full(msg)}", "on_message::ai")
                try:
                    reverse_reply = random_chance(self.probability)
                    ai_context = await self._get_ai_context(msg, ch_id)
                    self._record_ai_context(msg, text, ch_id)
                    async with msg.channel.typing():
                        reply = await self._get_ai_reply(
                            self._format_ai_text(msg, query),
                            self._format_ai_author(msg.author),
                            ai_context,
                            reverse_reply,
                            self._get_ai_session_id(ch_id),
                        )
                        if reverse_reply and reply != AI_REQUEST_FAILED:
                            reply = fullreverse(reply)
                        for reply_msg in await self._send_discord_reply_chain(msg, reply):
                            self._record_ai_context(reply_msg, reply_msg.content, ch_id)
                except Exception as e:
                    log.error(e, "on_message::ai")
                    try:
                        await msg.reply(AI_REQUEST_FAILED, mention_author=True)
                    except (
                        discord.Forbidden,
                        discord.DiscordServerError,
                        discord.HTTPException,
                    ) as e:
                        log.warn(e, "on_message::ai")
                return

            self._record_ai_context(msg, text, ch_id)

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
                    random.choices((REACTION_IMGS["toolong"], REACTION_IMGS["essay"]), (3, 1))[0],
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
            if "thè" in text_lower or "thé" in text_lower:
                log.debug(f'React "Tea": {format_msg_full(msg)}', "on_message::react")
                await msg.add_reaction("🍵")

        except (discord.Forbidden, discord.DiscordServerError) as e:
            log.warn(e, "on_message")
        except Exception as e:  # also discord.NotFound, discord.HTTPException
            log.error(e, "on_message")
        finally:
            self.active_messages -= 1
            if self.shutting_down and self.active_messages == 0 and self.shutdown_waiter:
                self.shutdown_waiter.set()

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
                    return_list.append(
                        (msg.reply, {"content": REACTION_IMGS[command], "mention_author": False})
                    )

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

    def _handle_urlfix(
        self, msg: discord.Message, text: str
    ) -> list[tuple[Callable[[], Any], dict[str, Any]]]:
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
        if self.shutting_down:
            log.warn("Received SIGINT again, forcing exit...", "_handle_ctrlc")
            sys.exit(1)

        log.info("Received SIGINT, waiting for active messages...", "_handle_ctrlc")
        self.shutting_down = True
        self.loop.create_task(self._shutdown())

    async def _shutdown(self) -> None:
        if self.active_messages > 0:
            self.shutdown_waiter = asyncio.Event()
            await self.shutdown_waiter.wait()

        if self.clear_cache:
            self._clear_cache()
            log.info("Cleared cache", "_shutdown")
        await self.close()

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

        # Ensure cache sub-keys exist.
        for key, default in INIT_DATA["cache"].items():
            self.data["cache"].setdefault(key, default)

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

    def _is_admin(self, msg: discord.Message) -> bool:
        return getattr(getattr(msg, "author", None), "id", None) in AI_ADMIN_USER_IDS

    def _get_ai_query(self, msg: discord.Message, text: str) -> str | None:
        query = None
        trigger = re.match(rf"{re.escape(AI_TRIGGER.rstrip())}\s+", text, re.I)
        if trigger:
            query = text[trigger.end() :]
        elif self.user:
            mention = re.match(rf"<@!?{self.user.id}>\s+", text)
            if mention:
                query = text[mention.end() :]
            else:
                reference = getattr(msg, "reference", None)
                resolved = getattr(reference, "resolved", None) if reference else None
                if (
                    resolved
                    and isinstance(resolved, discord.Message)
                    and resolved.author == self.user
                ):
                    query = text

        if query is None or not query.strip():
            return None
        if not self.test and self.user and self.user not in getattr(msg, "mentions", []):
            reference = getattr(msg, "reference", None)
            resolved = getattr(reference, "resolved", None) if reference else None
            if not (
                resolved and isinstance(resolved, discord.Message) and resolved.author == self.user
            ):
                return None
        return query.strip()

    def _format_ai_author(self, author: Any, include_extra: bool = True) -> str:
        _, display_name, extra = self._get_ai_author_info(author)
        if include_extra and extra:
            return f"{display_name} ({extra})"
        return display_name

    def _get_ai_author_info(self, author: Any) -> tuple[str, str, str]:
        user_id = getattr(author, "id", None)
        username = self._strip_discriminator(getattr(author, "name", None) or str(author))
        display_name = self._strip_discriminator(getattr(author, "display_name", None) or username)
        key = str(user_id) if user_id else display_name
        extras = []
        if username != display_name:
            extras.append(username)
        if user_id:
            extras.append(f"id={user_id}")
        return key, display_name, " ".join(extras)

    def _strip_discriminator(self, name: str) -> str:
        return re.sub(r"#\d{4}$", "", name)

    def _format_ai_text(self, msg: discord.Message, text: str) -> str:
        for user in getattr(msg, "mentions", []):
            author = self._format_ai_author(user, include_extra=False)
            text = text.replace(f"<@{user.id}>", f"@{author}")
            text = text.replace(f"<@!{user.id}>", f"@{author}")
        for channel in getattr(msg, "channel_mentions", []):
            text = text.replace(f"<#{channel.id}>", f"#{self._format_ai_channel(channel)}")

        parts = []
        reference = getattr(msg, "reference", None)
        resolved = getattr(reference, "resolved", None) if reference else None
        if resolved and isinstance(resolved, discord.Message):
            parts.append(
                f"replying_to: {self._format_ai_author(resolved.author)}: "
                f"{self._format_ai_text(resolved, resolved.content)}"
            )

        if text:
            parts.append(text)

        attachments = []
        for attachment in getattr(msg, "attachments", []):
            url = getattr(attachment, "url", None)
            if url:
                attachments.append(url)
        if attachments:
            parts.append(f"attachments: {' '.join(attachments)}")
        return "\n".join(parts)

    def _format_ai_channel(self, channel: Any) -> str:
        name = getattr(channel, "name", str(channel))
        channel_id = getattr(channel, "id", None)
        out = f"{name} id={channel_id}" if channel_id else str(name)
        topic = getattr(channel, "topic", None)
        if topic:
            out = f"{out}\ntopic: {topic}"
        return out

    def _format_ai_guild(self, guild: Any) -> str:
        if not guild:
            return "dm"
        name = getattr(guild, "name", str(guild))
        guild_id = getattr(guild, "id", None)
        return f"{name} id={guild_id}" if guild_id else str(name)

    def _record_ai_context(self, msg: discord.Message, text: str, ch_id: str) -> None:
        if any(x.message_id == msg.id for x in self.ai_message_context):
            return
        author_key, display_name, author_extra = self._get_ai_author_info(msg.author)
        self.ai_message_context.append(
            AiContextMessage(
                created_at=timer(),
                channel_id=ch_id,
                message_id=msg.id,
                author_key=author_key,
                display_name=display_name,
                author_extra=author_extra,
                content=self._format_ai_text(msg, text),
            )
        )
        self._prune_ai_context()

    def _update_ai_context_message(self, msg: discord.Message, text: str) -> None:
        for context_msg in self.ai_message_context:
            if context_msg.message_id == msg.id:
                author_key, display_name, author_extra = self._get_ai_author_info(msg.author)
                context_msg.author_key = author_key
                context_msg.display_name = display_name
                context_msg.author_extra = author_extra
                context_msg.content = self._format_ai_text(msg, text)
                return

    def _remove_ai_context_message(self, msg_id: int) -> None:
        self.ai_message_context = [x for x in self.ai_message_context if x.message_id != msg_id]

    def _remove_ai_context_messages(self, msg_ids: set[int]) -> None:
        self.ai_message_context = [
            x for x in self.ai_message_context if x.message_id not in msg_ids
        ]

    def _prune_ai_context(self) -> None:
        min_time = timer() - AI_CONTEXT_MAX_AGE_SECONDS
        self.ai_message_context = [x for x in self.ai_message_context if x.created_at >= min_time]

    async def _get_ai_context(self, msg: discord.Message, ch_id: str) -> str:
        self._prune_ai_context()
        context = [x for x in self.ai_message_context if x.channel_id == ch_id]
        if len(context) < AI_CONTEXT_MAX_MESSAGES:
            context = await self._fetch_ai_context(msg, ch_id, context)
        context = context[-AI_CONTEXT_MAX_MESSAGES:]
        messages = self._format_ai_context_messages(context)
        return f"""<context>
<metadata>
self: {self._format_ai_author(self.user)}
server: {self._format_ai_guild(msg.guild)}
channel: {self._format_ai_channel(msg.channel)}
</metadata>

<messages>
{messages}
</messages>
</context>"""

    def _format_ai_context_messages(self, context: list[AiContextMessage]) -> str:
        seen_authors = set()
        messages = []
        for context_msg in context:
            include_extra = context_msg.author_key not in seen_authors
            seen_authors.add(context_msg.author_key)
            author = context_msg.display_name
            if include_extra and context_msg.author_extra:
                author = f"{context_msg.display_name} ({context_msg.author_extra})"
            messages.append(
                f'<message id="{html.escape(str(context_msg.message_id), quote=True)}" '
                f'author="{html.escape(author, quote=True)}">\n'
                f"{html.escape(context_msg.content)}\n"
                f"</message>"
            )
        return "\n".join(messages)

    async def _fetch_ai_context(
        self,
        msg: discord.Message,
        ch_id: str,
        context: list[AiContextMessage],
    ) -> list[AiContextMessage]:
        history = getattr(msg.channel, "history", None)
        if not history:
            return context

        min_created_at = datetime.now(timezone.utc).timestamp() - AI_CONTEXT_MAX_AGE_SECONDS
        seen = {x.message_id for x in context}
        fetched: list[AiContextMessage] = []
        try:
            async for old_msg in history(limit=AI_CONTEXT_MAX_MESSAGES, before=msg):
                created_at = old_msg.created_at.replace(tzinfo=timezone.utc).timestamp()
                if created_at < min_created_at:
                    break
                if old_msg.id in seen or not old_msg.content:
                    continue
                author_key, display_name, author_extra = self._get_ai_author_info(old_msg.author)
                fetched.append(
                    AiContextMessage(
                        created_at=timer(),
                        channel_id=ch_id,
                        message_id=old_msg.id,
                        author_key=author_key,
                        display_name=display_name,
                        author_extra=author_extra,
                        content=self._format_ai_text(old_msg, old_msg.content),
                    )
                )
        except (discord.Forbidden, discord.HTTPException) as e:
            log.warn(e, "on_message::ai_context")
            return context

        return fetched[::-1] + context

    async def _get_ai_reply(
        self,
        query: str,
        author: str = "",
        context: str = "",
        harness_will_reverse_output: bool = False,
        session_id: str | None = None,
    ) -> str:
        content = self._format_ai_request_content(
            query, author, context, harness_will_reverse_output
        )

        payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        }
        if session_id:
            payload["session_id"] = session_id[:256]
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "HTTP-Referer": "https://github.com/Anurag-Shah/TobEgassem",
            "X-Title": "TobEgassem",
        }
        url = f"{self.openai_base_url}/chat/completions"
        if self.openai_web_search:
            payload["tools"] = [{"type": "openrouter:web_search"}]
        timeout = aiohttp.ClientTimeout(total=AI_REQUEST_TIMEOUT_SECONDS)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(1, AI_REQUEST_MAX_ATTEMPTS + 1):
                reply, retry_after = await self._request_ai_reply(session, url, payload, headers)
                if reply:
                    return reply
                if attempt == AI_REQUEST_MAX_ATTEMPTS:
                    break

                delay = self._get_ai_retry_delay(attempt, retry_after)
                log.warn(
                    f"AI request failed, retrying in {delay:.1f}s "
                    f"({attempt}/{AI_REQUEST_MAX_ATTEMPTS})",
                    "on_message::ai",
                )
                await asyncio.sleep(delay)

        return AI_REQUEST_FAILED

    def _get_ai_session_id(self, ch_id: str) -> str:
        return f"discord-channel-{ch_id}"[:256]

    def _format_ai_request_content(
        self,
        query: str,
        author: str = "",
        context: str = "",
        harness_will_reverse_output: bool = False,
    ) -> str:
        request = f"""<request>
<metadata>
current_time: {datetime.now(timezone.utc).isoformat()}
harness_will_reverse_output: {str(harness_will_reverse_output).lower()}
</metadata>

<query author={author!r}>
{query}
</query>
</request>"""
        if context:
            return f"{context}\n\n{request}"
        return request

    async def _request_ai_reply(
        self,
        session: aiohttp.ClientSession,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[str | None, float | None]:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                text = await response.text()
                retry_after = self._parse_ai_retry_after(text, response.headers)
                if response.status >= 400:
                    log.warn(text, "on_message::ai")
                    return None, retry_after
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            log.warn(f"AI request error: {e}", "on_message::ai")
            return None, None

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.warn(f"AI response was not JSON: {text}", "on_message::ai")
            return None, None

        self._log_ai_usage(data)
        reply = self._extract_ai_reply(data)
        if reply:
            return reply, None

        log.warn(f"AI response missing content: {text}", "on_message::ai")
        return None, self._parse_ai_retry_after(text)

    def _log_ai_usage(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return
        details = usage.get("prompt_tokens_details")
        if not isinstance(details, dict):
            return
        cached_tokens = details.get("cached_tokens")
        cache_write_tokens = details.get("cache_write_tokens")
        if cached_tokens or cache_write_tokens:
            log.debug(
                f"AI cache usage: cached_tokens={cached_tokens or 0} "
                f"cache_write_tokens={cache_write_tokens or 0}",
                "on_message::ai",
            )

    def _extract_ai_reply(self, data: Any) -> str | None:
        if not isinstance(data, dict):
            return None
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        choice = choices[0]
        if not isinstance(choice, dict):
            return None
        message = choice.get("message")
        if not isinstance(message, dict):
            return None
        content = message.get("content")
        if isinstance(content, str):
            return content.strip() or None
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
            return "".join(parts).strip() or None
        return None

    def _parse_ai_retry_after(self, text: str, headers: Any | None = None) -> float | None:
        if headers:
            retry_after = headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        error = data.get("error")
        if not isinstance(error, dict):
            return None
        metadata = error.get("metadata", {})
        if not isinstance(metadata, dict):
            return None
        retry_after = metadata.get("retry_after_seconds")
        if isinstance(retry_after, int | float):
            return float(retry_after)
        return None

    def _get_ai_retry_delay(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is None:
            retry_after = AI_RETRY_DELAY_SECONDS * 2 ** (attempt - 1)
        return min(retry_after, AI_RETRY_MAX_DELAY_SECONDS)

    async def _send_discord_reply_chain(
        self, msg: discord.Message, reply: str
    ) -> list[discord.Message]:
        reply_msgs = []
        previous_msg = msg
        for chunk in self._split_discord_reply(reply):
            reply_msg = await previous_msg.reply(chunk, mention_author=not reply_msgs)
            reply_msgs.append(reply_msg)
            previous_msg = reply_msg
        return reply_msgs

    def _split_discord_reply(self, reply: str) -> list[str]:
        chunks = []
        reply = reply.strip()
        while len(reply) > DISCORD_MESSAGE_MAX_LENGTH:
            split_at = reply.rfind("\n", 0, DISCORD_MESSAGE_MAX_LENGTH + 1)
            if split_at <= 0:
                split_at = reply.rfind(" ", 0, DISCORD_MESSAGE_MAX_LENGTH + 1)
            if split_at <= 0:
                split_at = DISCORD_MESSAGE_MAX_LENGTH

            chunk = reply[:split_at].rstrip()
            if chunk:
                chunks.append(chunk)
            reply = reply[split_at:].lstrip()

        if reply:
            chunks.append(reply)
        return chunks or [""]

    def _valid_message(self, msg: discord.Message) -> bool:
        ch_id = str(msg.channel.id)
        g_id = str(msg.guild.id) if msg.guild else ""
        return (ch_id not in self.data["blocked_channels"]) and (
            ch_id in self.data["channels"] or g_id in self.data["guilds"]
        )

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
