#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dotenv import load_dotenv

from tob import Tob
from utils.utils import env, env_opt


def main():
    load_dotenv()

    bot_token = env("DISCORD_BOT_TOKEN")
    twitter_tokens = env("TWITTER_TOKENS")
    log_level = env_opt("LOG_LEVEL")
    reply_to_invalid = env_opt("REPLY_TO_INVALID")
    log_color = env_opt("LOG_COLOR")
    clear_cache = env_opt("CLEAR_CACHE")

    tob = Tob(
        twitter_tokens=twitter_tokens,
        log_level=log_level,
        reply_to_invalid_command=reply_to_invalid,
        log_color=log_color,
        clear_cache=clear_cache,
    )

    tob.run(bot_token)


if __name__ == "__main__":
    main()
