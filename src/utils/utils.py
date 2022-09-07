import json
import os
import re
from typing import Any

import discord
import tweepy


def env(s: str) -> str:
    _s = os.getenv(s)
    if _s == None or _s == "":
        raise EnvironmentError(f"Missing {s} environment variable")
    return _s


def env_opt(s: str, default: str|None = None) -> Any:
    _s = os.getenv(s)
    return _s if _s else default


def env_arg(args: dict, env: str, name: str, default: Any|None = None):
    s = os.getenv(env)
    if s is not None:
        args[name] = s
    elif default is not None:
        args[name] = default
    else:
        raise EnvironmentError(f"Missing '{env}' environment variable")


def to_bool(v: Any) -> bool:
    if isinstance(v, str):
        return v.lower() in ("y", "yes", "t", "true", "1")
    return bool(v)


def get_tweepy_api_from_string(tw_tokens: str) -> tweepy.API:
    tw_info = tw_tokens.split(";")
    if not ";" in tw_tokens or len(tw_info) != 4:
        raise EnvironmentError(f"Invalid {tw_tokens} environment variable: bad format")
    tw_access_token = tw_info[0]
    ts_access_secret = tw_info[1]
    tw_consumer_key = tw_info[2]
    tw_consumer_secret = tw_info[3]

    auth = tweepy.OAuth1UserHandler(
        tw_consumer_key,
        tw_consumer_secret,
        tw_access_token,
        ts_access_secret,
    )

    return tweepy.API(auth)


def format_msg(msg: discord.Message) -> str:
    return f'<MSG>"{msg.content}"</MSG>'


def format_msg_full(msg: discord.Message) -> str:
    return f'{msg.author} @ {msg.guild} #{msg.channel}: <MSG>"{msg.content}"</MSG>'


def fullreverse(message: str):
    parens_list: list[tuple[str, str]] = [(")", "("), ("}", "{"), ("]", "[")]
    delimiters = re.compile(r"<(?:&|#|@!|:.+:)[0-9]+>")

    parens = {y: x for x, y in parens_list}
    parens.update(parens_list)
    out = [(parens[x] if x in parens else x) for x in message[::-1]]

    delimited = re.finditer(delimiters, message)
    for match in delimited:
        out[len(message) - match.end() : len(message) - match.start()] = match.group()

    return "".join(out)


def readf(fname: str):
    with open(fname, "r") as f:
        return json.load(f)


def writef(fname: str, data: Any) -> None:
    with open(fname, "w") as f:
        json.dump(data, f)


def get_seed(data: Any) -> float:
    seed: float = 0.0
    # no .len()
    if isinstance(data, (bool, int, float)):
        seed += data
    else:
        seed += len(data)
        if isinstance(data, dict):
            for key in data.keys():
                seed += get_seed(key)
                seed += get_seed(data[key])
        elif isinstance(data, list):
            for value in data:
                seed += get_seed(value)

    return seed


# def _underscore(s: Any) -> str:
#     return "_".join(str(s).split(" "))


def ends_with(s: str, l: list[str]) -> bool:
    for x in l:
        if s.endswith(x):
            return True
    return False
