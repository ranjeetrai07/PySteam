# PySteam :shipit:

Python interface for Steam Web Chat.

Ported from [node-steamcommunity](https://github.com/DoctorMcKay/node-steamcommunity).
Includes a port of [node-steamid](https://github.com/DoctorMcKay/node-steamid) as well.

## Packages Required

    pip install requests pycrypto pyee enum34 pyquery

`py.test` also needs to be installed for testing, if developing.


## Usage

`import` the Steam API

```python
import steamapi as SteamAPI
steam = SteamAPI.SteamAPI()
```

Define the events you need to respond to with the `pyee` event decorators.

The current events emitted are:

* `chatPersonaState`
    - `steamID`: instance of [`SteamID.SteamID`](#quick-tangent-steamid) for the [persona](#persona-data) which changed
    - `nextPersona`: the newly updated [persona](#persona-data)
    - `prevPersona`: the last [persona](#persona-data) stored
* `chatMessage`
    - `sender`: instance of [`SteamID.SteamID`](#quick-tangent-steamid), containing the sender's ID
    - `message`: the message the sender has sent
* `chatTyping`
    - `sender`: instance of [`SteamID.SteamID`](#quick-tangent-steamid), containing the typing user's ID

Which can be invoked like so:

```python
@steam.event.on('chatPersonaState')
def chatPersonaStateHandler(steamID, nextPersona, prevPersona):
    pass

@steam.event.on('chatMessage')
def chatMessageHandler(steamID, text):
    print steam.chatFriends[steamID]["personaName"] + ':', text
    if text.lower() == "ping":
        steam.chatMessage(sender, "pong")

@steam.event.on('chatTyping')
def chatTypingHandler(steamID):
    pass
```

Logging in can be achieved through this code snippet:

```python
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
```

Status will be `SteamAPI.LoginStatus.LoginSuccessful` once you have logged in.
From here, you can call `steam.chatLogon()` to initiate a connection with the chat API.

After you have logged in, `steam.chatFriends` will be populated with the [persona](#persona-data) of the users on your friends list, as a dict with their `SteamID64` as the key.

Nothing will be needed past this in terms of Steam connection.
Once you have finished doing what you're doing, call `steam.chatLogoff()` to gracefully disconnect from the Steam servers.


## Quick Tangent: SteamID

I have also ported `node-steamid` to Python. It can be initialized with:

* `STEAM_0:0:34589227` (Steam ID2)
* `[U:1:69178454]` (Steam ID3)
* `76561198029444182` (Steam64 ID)
* `69178454` (Steam32 ID)

In these examples, `sid = SteamID.SteamID('STEAM_0:0:34589227')`
It exposes these methods:

* `sid.isValid()`
* `sid.Steam2RenderedID()`
* `sid.Steam3RenderedID()`

And these properties:

* `sid.accountid`
* `sid.type`
* `sid.instance`
* `sid.universe`

Rendered Forms (properties):

* `sid.SteamID64` (e.g. `76561198029444182`)
* `sid.SteamID32` (e.g. `69178454`)
* `sid.SteamID` (e.g. `STEAM_0:0:34589227`)
* `sid.SteamID3` (e.g. `[U:1:69178454]`)

## Persona Data

A **persona** is a dictionary of user info, usually like so:

```python
{
    'avatarHash': '848eaefc30b56c57c03d4c0d7e4e796a138fdccc',
    'inGame': True,
    'inGameAppID': '240',
    'inGameName': 'Counter-Strike: Source',
    'personaName': 'anzu',
    'personaState': <PersonaState.Away: 3>,
    'personaStateFlags': <PersonaStateFlag.Default: 0>,
    'steamID': SteamID.SteamID('76561198029444182')
}
```

* `avatarHash` is the hash of the user's Steam avatar.
    * Use `SteamAPI.urlForAvatarHash(avatarHash)` to get the full URL.
* `inGame` is a boolean describing if the user is currently playing a game on Steam or not.
* `inGameAppID` is the Steam AppID of the game currently being played if `inGame` is true, else it is `None`.
* `inGameAppID` is the name of the game currently being played if `inGame` is true, else it is `None`.
* `personaName` is the steam nickname set by the user.
* `personaState` is the user's online status on Steam. One of:
    * `SteamAPI.PersonaState.Offline`
    * `SteamAPI.PersonaState.Online`
    * `SteamAPI.PersonaState.Busy`
    * `SteamAPI.PersonaState.Away`
    * `SteamAPI.PersonaState.Snooze`
    * `SteamAPI.PersonaState.LookingToTrade`
    * `SteamAPI.PersonaState.LookingToPlay`
* `personaStateFlags` describes if the user is using a special mode of Steam in chat.
    * `HasRichPresence`
    * `InJoinableGame`
    * `OnlineUsingWeb`
    * `OnlineUsingMobile`
    * `OnlineUsingBigPicture`
* `steamID` is an instance of [`SteamID.SteamID`](#quick-tangent-steamid).


## Sending Messages

Messages can be sent via the `steam.chatMessage` method.

```python
steam.chatMessage(SteamID64, message)
```