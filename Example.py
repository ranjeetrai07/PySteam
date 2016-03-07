import SteamAPI
steam = SteamAPI.SteamAPI()


@steam.event.on('chatPersonaState')
def chatPersonaState(steamID, persona, old_persona, difference):
    if difference:
        print difference


@steam.event.on('chatMessage')
def chatMessage(sender, text):
    print steam.chatFriends[sender]["personaName"] + ':', text
    if text.lower() == "ping":
        steam.chatMessage(sender, "pong")


username = raw_input("Username: ")
password = raw_input("Password: ")

status = steam.login({"accountName": str(username), "password": str(password)})
if status == SteamAPI.LoginStatus.TwoFactor:
    token = raw_input("Two-factor Token: ")
    status = steam.retry({"two-factor": token})
elif status == SteamAPI.LoginStatus.SteamGuard:
    steamguard = raw_input("SteamGuard Code: ")
    status = steam.retry({"steamguard": steamguard})

if status == SteamAPI.LoginStatus.LoginSuccessful:
    steam.chatLogon()
    # raw_input("press enter to exit.")
    import IPython
    IPython.embed()
    steam.chatLogoff()
else:
    print "Couldn't authenticate."
