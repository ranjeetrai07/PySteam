from sys import argv
import IPython
from builtins import input

import steamapi as SteamAPI
steam = SteamAPI.SteamAPI()

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

print("steamguard:", steam.steamguard)
print("oAuthToken:", steam.oAuthToken)

steamguard = steam.steamguard
oauthtoken = steam.oAuthToken

# logoff
steam.session.cookies.clear()
steam = SteamAPI.SteamAPI()
# use tokens to login.
print(steam.oAuthLogin(steamguard, oauthtoken))

IPython.embed()
