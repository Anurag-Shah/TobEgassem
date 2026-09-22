#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config import load_config
from tob import Tob


def main():
    config = load_config()
    bot_token = config.pop("discord_bot_token")
    tob = Tob(**config)
    tob.run(bot_token)


if __name__ == "__main__":
    main()
