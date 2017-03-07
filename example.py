from sys import argv
import IPython
from builtins import input

import steamapi as SteamAPI
steam = SteamAPI.SteamAPI()


@steam.event.on('chatPersonaState')
def chatPersonaState(steamID, persona, old_persona):
    diff = SteamAPI.dictDiff(persona, old_persona)
    if diff:
        print(diff)


@steam.event.on('chatMessage')
def chatMessage(sender, text):
    print(steam.chatFriends[str(sender.SteamID64)]["personaName"] + ':', text)
    if text.lower() == "ping":
        steam.chatMessage(sender, "pong")

try:
    username = argv[1]
    password = argv[2]
except IndexError:
    username = input("username: ")
    password = input("password: ")

status = steam.login(username=username, password=password)
while status != SteamAPI.LoginStatus.LoginSuccessful:
    if status == SteamAPI.LoginStatus.TwoFactor:
        token = input("Two-factor Token: ")
        status = steam.retry(twofactor=token)
    elif status == SteamAPI.LoginStatus.SteamGuard:
        steamguard = input("SteamGuard Code: ")
        status = steam.retry(steamguard=steamguard)
    elif status == SteamAPI.LoginStatus.Captcha:
        captcha = input("CAPTCHA: ")
        status = steam.retry(captcha=captcha)

steam.chatLogon()
IPython.embed()
steam.chatLogoff()
