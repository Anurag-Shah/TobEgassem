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
You will need to setup a discord bot, a twitter application, and get the correct tokens from those setup as environment variables (refer to `src/main.py` for the environment variables needed). Set `ENABLE_AI=true` and `OPENAI_API_KEY` to enable AI replies. The example config uses OpenRouter with `openai/gpt-5-nano` and low reasoning; include `ultrathink` in a prompt to use high reasoning for that request. Set `OPENAI_WEB_SEARCH=true` to allow Tob to browse the web via OpenRouter's `openrouter:web_search` server tool.

(For access to the running instance of the bot, please DM me on discord at `Sol_InvictusXLII#1306`).

Install dependencies with `uv sync` and run with `uv run python src/main.py`. Run tests with `uv run pytest`.

## Contributing
Please fork the repository and document your changes in the pull request.
