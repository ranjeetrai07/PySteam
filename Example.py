import SteamAPI
steam = SteamAPI.SteamAPI()


@steam.event.on('chatPersonaState')
def chatPersonaState(steamID, persona, old_persona):
    diff = SteamAPI.dictDiff(persona, old_persona)
    if diff:
        print diff


@steam.event.on('chatMessage')
def chatMessage(sender, text):
    print steam.chatFriends[sender]["personaName"] + ':', text
    if text.lower() == "ping":
        steam.chatMessage(sender, "pong")


username = str(raw_input("Username: "))
password = str(raw_input("Password: "))
# from sys import argv
# username = argv[1]
# password = argv[2]

status = steam.login(username=username, password=password)
if status == SteamAPI.LoginStatus.TwoFactor:
    token = raw_input("Two-factor Token: ")
    status = steam.retry(twofactor=token)
elif status == SteamAPI.LoginStatus.SteamGuard:
    steamguard = raw_input("SteamGuard Code: ")
    status = steam.retry(steamguard=steamguard)

if status == SteamAPI.LoginStatus.LoginSuccessful:
    steam.chatLogon()
    # raw_input("press enter to exit.")
    import IPython
    IPython.embed()
    steam.chatLogoff()
else:
    print "Couldn't authenticate."
