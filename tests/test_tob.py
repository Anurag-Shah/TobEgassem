def test_example():
    pass


# TODO
# import asyncio

# import discord

# import tob
# import log
# import utils

# user_id = 0
# msg_id = 0


# def get_user() -> discord.User:
#     global user_id
#     test_user_data = {
#         "username": "doni",
#         "id": str(user_id),
#         "discriminator": "#0000",
#         "avatar": "http://bruhngus.com/avatar.jpg",
#         "public_flags": 0,
#         "bot": False,
#         "system": False,
#     }
#     user_id += 1
#     return discord.User(state=None, data=test_user_data)


# def get_message(content: str, expected: any) -> discord.Message:
#     global msg_id
#     test_user = get_user()

#     class State:
#         def store_user(*_, **__):
#             return None

#     class Channel:
#         def __init__(self) -> None:
#             self.id = 1

#         async def send(c: any, *_, **__):
#             log.info(f'CONTENT  = "{c}"')
#             log.info(f'EXPECTED = "{expected}"')
#             return None

#     test_state = State()
#     test_channel = Channel()
#     test_message_data = {
#         "content": content,
#         "id": str(msg_id),
#         "author": test_user,
#         "attachments": [],
#         "embeds": [],
#         "edited_timestamp": "",
#         "type": "",
#         "pinned": False,
#         "mention_everyone": False,
#         "tts": False,
#     }
#     msg_id += 1
#     msg = discord.Message(
#         state=test_state,
#         channel=test_channel,
#         data=test_message_data,
#     )
#     return msg


# class TestTob:
#     tob = tob.Tob(twitter_tokens=";;;;", test=True, log_level=5)

#     def test_url_substitution(self):
#         test_message_content = """Media discordapp net

#     media.discordapp.net
#     media.discordapp.net/bruhngus
#     media.discordapp.net/bruhngus/bruhng
#     media.discordapp.net/bruhngus/bruhng/us

#     https://media.discordapp.net
#     https://media.discordapp.net/bruhngus
#     https://media.discordapp.net/bruhngus/bruhng
#     https://media.discordapp.net/bruhngus/bruhng/us

#     IMG

#     twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ

#     https://twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ

#     <twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ>

#     <https://twitter.com/POTUS/status/1553120835686252544?s=20&t=3HCyDORTavdzSmYG03i5hQ>

#     VIDEO

#     twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ

#     https://twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ

#     <twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ>

#     <https://twitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ>"""
#         test_expected_result = "\n".join(
#             [
#                 "https://cdn.discordapp.com",
#                 "https://cdn.discordapp.com/bruhngus",
#                 "https://cdn.discordapp.com/bruhngus/bruhng",
#                 "https://cdn.discordapp.com/bruhngus/bruhng/us",
#                 "https://cdn.discordapp.com",
#                 "https://cdn.discordapp.com/bruhngus",
#                 "https://cdn.discordapp.com/bruhngus/bruhng",
#                 "https://cdn.discordapp.com/bruhngus/bruhng/us",
#                 "https://vxtwitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ",
#                 "https://vxtwitter.com/POTUS/status/1553479370383171584?s=20&t=3HCyDORTavdzSmYG03i5hQ",
#             ]
#         )
#         test_message = get_message(test_message_content, test_expected_result)

#         asyncio.run(self.tob.on_message(test_message))
