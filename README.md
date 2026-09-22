# Tob

### Tob is a discord bot that reverses 1/69 messages.

## Features
- Channel/Server wide toggle: Use `|server add` to enable tob serverwide, or `|channel add` to enable tob in a particular channel. This will allow tob to reverse messages in those channels.
- media.discordapp.net and twitter.com url replacement: replaces these urls for better embed solutions on pc and mobile, for certain file types
- Reacts to certain keywords
- Self promotion (of my youtube channel) 😎
- Bruhngus
- AI replies via an OpenAI-compatible API when Tob is tagged with `@tob <query>`

## Running the bot
Copy `config.example.json` to `config.json` in the repository root and fill in your Discord bot token and Twitter tokens. The Twitter token format is `access_token;access_secret;consumer_key;consumer_secret`. Config uses JSON booleans and integers; `config.json` is gitignored and contains credentials. Environment variables and `.env` are no longer read.

Set `enable_ai` to `true` and fill in `openai_api_key` to enable AI replies. Tob detects OpenRouter (`sk-or-v1-`) and OrcaRouter (`sk-orca-`) keys and sends each provider's reasoning and web-search format. The example config uses OpenRouter with `openai/gpt-5-nano` and low reasoning; include `ultrathink` in a prompt to use high reasoning for that request. Add `--no-context` to an AI prompt to omit surrounding channel history for that request. Set `openai_web_search` to `true` to allow Tob to browse the web.

## Admin settings

Users in the existing admin ID allowlist can read and update non-sensitive settings through Discord. Use an actual bot mention or the literal `@tob` prefix. Keys are case-insensitive.

- `@tob config` lists all readable settings and their current values, including defaults.
- `@tob config reload` reloads the settings below from disk without a restart. Missing settings revert to defaults; invalid files leave live settings unchanged.
- `@tob config key` reads one setting, for example `@tob config enable_ai`.
- `@tob config key=value` changes one setting, for example `@tob config enable_ai=true` or `@tob config probability=100`. Changes take effect immediately and persist to `config.json`.

| Key | Values |
| --- | --- |
| `enable_ai`, `openai_web_search` | `true` or `false` |
| `openai_model` | Model ID, such as `openai/gpt-5-nano` |
| `openai_reasoning_effort` | `none`, `minimal`, `low`, `medium`, `high`, `xhigh` (provider support varies) |
| `probability` | Positive integer; reverses 1 in this many messages |
| `twitter_replacement` | Hostname, such as `vxtwitter.com` |
| `reply_to_invalid_command`, `clear_cache`, `log_color` | `true` or `false` |
| `log_level` | Integer from 0 (off) to 5 (trace) |

Only the settings above can be read or changed through Discord. Tokens, API keys, the API endpoint, and admin IDs stay hidden. Edit credentials and the endpoint in the file and restart the bot. Admin commands bypass AI processing, context storage, and message logging.

(For access to the running instance of the bot, please DM me on discord at `Sol_InvictusXLII#1306`).

Install dependencies with `uv sync` and run with `uv run python src/main.py`. Run tests with `uv run pytest`.

## Contributing
Please fork the repository and document your changes in the pull request.
