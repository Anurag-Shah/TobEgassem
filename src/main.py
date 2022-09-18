#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dotenv import load_dotenv

from tob import Tob
from utils.utils import env, env_arg
from typing import Any


def main():
    load_dotenv()

    bot_token = env("DISCORD_BOT_TOKEN")
    args: dict[str, Any] = {}
    env_arg(args, "TWITTER_TOKENS", "twitter_tokens")
    env_arg(args, "LOG_LEVEL", "log_level", default=1)
    env_arg(args, "REPLY_TO_INVALID_COMMAND", "reply_to_invalid_command", default=False)
    env_arg(args, "LOG_COLOR", "log_color", default=False)
    env_arg(args, "CLEAR_CACHE", "clear_cache", default=False)

    tob = Tob(**args)
    tob.run(bot_token)


if __name__ == "__main__":
    main()
