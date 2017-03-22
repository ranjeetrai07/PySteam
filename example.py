from sys import argv
import IPython
from builtins import input

import steamapi
steam = steamapi.steamapi()


@steam.event.on('chat_persona_state')
def chat_persona_state(steam_id, persona, old_persona):
    diff = steamapi.utils.dict_diff(persona, old_persona)
    if diff:
        print(diff)


@steam.event.on('chat_message')
def chat_message(sender, text, own):
    # keep in mind that when `own` is true, the sender is infact
    # the recipient of the message, with the actual sender being
    # `steam.steamID` (yourself)
    # (you can get your own persona through `steam.account_persona`)
    # this only happens when using multiple clients for chat AFAIK

    friend = steam.chat.friends[str(sender.as_64)]
    if not own:
        print("({nickname}) {name}: {text}".format(text=text, **friend))
    else:
        yourself = steam.chat.account_persona.name
        formatted = "{yourself} -> ({nickname}) {name}: {text}"
        print(formatted.format(text=text, yourself=yourself,
                               name=friend.name, nickname=friend.nickname))

    if text.lower() == "ping":
        steam.chat.send_message(sender, "pong")

try:
    username = argv[1]
    password = argv[2]
except IndexError:
    username = input("username: ")
    password = input("password: ")

status = steam.login(username=username, password=password)
while status != steamapi.enums.LoginStatus.LoginSuccessful:
    if status == steamapi.enums.LoginStatus.TwoFactor:
        token = input("Two-factor Token: ")
        status = steam.retry(twofactor=token)
    elif status == steamapi.enums.LoginStatus.SteamGuard:
        steamguard = input("SteamGuard Code: ")
        status = steam.retry(steamguard=steamguard)
    elif status == steamapi.enums.LoginStatus.Captcha:
        captcha = input("CAPTCHA: ")
        status = steam.retry(captcha=captcha)

steam.chat.login()
IPython.embed()
steam.chat.logout()
