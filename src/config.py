import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

# Only these settings can be read or changed through Discord.
DEFAULT_SETTINGS = {
    "enable_ai": False,
    "openai_model": "gpt-4o-mini",
    "openai_reasoning_effort": "low",
    "openai_web_search": False,
    "probability": 69,
    "twitter_replacement": "vxtwitter.com",
    "reply_to_invalid_command": False,
    "clear_cache": False,
    "log_level": 1,
    "log_color": False,
}
EDITABLE_SETTINGS = {key: type(value) for key, value in DEFAULT_SETTINGS.items()}


def validate_setting(key: str, value: Any) -> Any:
    kind = EDITABLE_SETTINGS.get(key)
    if kind is None:
        raise ValueError("Setting is not editable.")
    if type(value) is not kind:
        raise ValueError("Invalid value type.")
    if key == "probability" and value < 1:
        raise ValueError("Probability must be a positive integer.")
    if key == "log_level" and not 0 <= value <= 5:
        raise ValueError("Log level must be between 0 and 5.")
    if key == "openai_reasoning_effort" and value not in (
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    ):
        raise ValueError("Invalid reasoning effort.")
    if key == "openai_model" and not re.fullmatch(r"[a-zA-Z0-9_./:-]{1,200}", value):
        raise ValueError("Invalid model name.")
    if key == "twitter_replacement" and not re.fullmatch(
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}", value
    ):
        raise ValueError("Invalid replacement hostname.")
    return value


def parse_setting(key: str, value: str) -> Any:
    kind = EDITABLE_SETTINGS.get(key)
    if kind is bool:
        if value.lower() not in ("true", "false"):
            raise ValueError("Use true or false.")
        parsed = value.lower() == "true"
    elif kind is int:
        if not re.fullmatch(r"[0-9]{1,9}", value):
            raise ValueError("Use an integer.")
        parsed = int(value)
    else:
        parsed = value
    return validate_setting(key, parsed)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = json.loads(path.read_text())
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object.")
    for key, value in config.items():
        if key in EDITABLE_SETTINGS:
            validate_setting(key, value)
        elif key not in (
            "discord_bot_token",
            "twitter_tokens",
            "openai_api_key",
            "openai_base_url",
        ):
            raise ValueError("Unknown config setting.")
        elif not isinstance(value, str):
            raise ValueError("Credentials and API endpoint must be strings.")
    for key in ("discord_bot_token", "twitter_tokens"):
        if not config.get(key):
            raise ValueError(f"Missing {key} in config.json.")
    return config


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    fd, name = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as file:
            json.dump(config, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
