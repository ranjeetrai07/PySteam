from sys import argv
import IPython
from builtins import input

import steamapi
steam = steamapi.steamapi()

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

print("steamguard:", steam.steamguard)
print("oAuthToken:", steam.oauth_token)

steamguard = steam.steamguard
oauthtoken = steam.oauth_token

# logoff
steam.session.cookies.clear()
steam = steamapi.steamapi()
# use tokens to login.
print(steam.oauth_login(steamguard, oauthtoken))

IPython.embed()
