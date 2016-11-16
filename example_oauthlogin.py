from sys import argv
import IPython

import steamapi as SteamAPI
steam = SteamAPI.SteamAPI()

try:
    username = argv[1]
    password = argv[2]
except IndexError:
    username = raw_input("username: ")
    password = raw_input("password: ")

status = steam.login(username=username, password=password)
while status != SteamAPI.LoginStatus.LoginSuccessful:
    if status == SteamAPI.LoginStatus.TwoFactor:
        token = raw_input("Two-factor Token: ")
        status = steam.retry(twofactor=token)
    elif status == SteamAPI.LoginStatus.SteamGuard:
        steamguard = raw_input("SteamGuard Code: ")
        status = steam.retry(steamguard=steamguard)
    elif status == SteamAPI.LoginStatus.Captcha:
        captcha = raw_input("CAPTCHA: ")
        status = steam.retry(captcha=captcha)

print "steamguard:", steam.steamguard
print "oAuthToken:", steam.oAuthToken

steamguard = steam.steamguard
oauthtoken = steam.oAuthToken

# logoff
steam.session.cookies.clear()
steam = SteamAPI.SteamAPI()
# use tokens to login.
print steam.oAuthLogin(steamguard, oauthtoken)

IPython.embed()
