import SteamAPI
steam = SteamAPI.SteamAPI()

# username = str(raw_input("Username: "))
# password = str(raw_input("Password: "))
from sys import argv
username = argv[1]
password = argv[2]

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
# logoff
steam._session.cookies.clear()
print steam.oAuthLogin(steam.steamguard, steam.oAuthToken)
import IPython
IPython.embed()
