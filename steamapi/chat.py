from __future__ import unicode_literals
import requests
import re
import json
from enum import IntEnum, unique
from . import *

# chat constants taken from chat.js
POLL_DEFAULT_TIMEOUT = 20
POLL_SUCCESS_INCREMENT = 5
POLL_MAX_TIMEOUT = 120


@unique
class ChatState(IntEnum):
    """Possible chat states.
    """
    Offline, LoggingOn, LogOnFailed, LoggedOn = list(range(4))


@unique
class PersonaState(IntEnum):
    """Possible online states.
    """
    Offline = 0
    Online = 1
    Busy = 2
    Away = 3
    Snooze = 4
    LookingToTrade = 5
    LookingToPlay = 6
    Max = 7


@unique
class FriendRelationship(IntEnum):
    """Possible friend relationship values.
    """
    NONE = 0
    Blocked = 1
    RequestRecipient = 2
    Friend = 3
    RequestInitiator = 4
    Ignored = 5
    IgnoredFriend = 6
    SuggestedFriend = 7
    Max = 8


@unique
class PersonaStateFlag(IntEnum):
    """Possible state flags.
    """
    Default = 0
    HasRichPresence = 1
    InJoinableGame = 2

    OnlineUsingWeb = 256
    OnlineUsingMobile = 512
    OnlineUsingBigPicture = 1024


def getWebApiOauthToken(self):
    """Retrieves necessary OAuth token for Steam Web chat.

    Returns
    -------
    str
        OAuth token to use for chat authentication
    """
    resp = self.session.get("https://steamcommunity.com/chat")
    if self._checkHttpError(resp):
        return ("HTTP Error", None)

    token = re.compile(r'"([0-9a-f]{32})" \);')
    matches = token.search(resp.text)
    if matches:
        self._initialLoadDetails(resp.text)
        return (None, matches.groups()[0])

    return ("Malformed Response", None)


def _initialLoadDetails(self, resp):
    """Parses the chat page for the initial persona details.

    The chat page is parsed for:
        - Your own persona details
          This is needed because the API is inconsistent and may or may not
          include yourself in the friend persona list
        - All friend persona details
        - Friends list groupings

    Parameters
    ----------
    resp : str
        The content of a page which has a call to CWebChat in its scripts
        (https://steamcommunity.com/chat/)
    """
    details_full = re.compile(r'WebAPI, (\{.*\}), (\[.*\]), (\[.*\]) \);')
    matches = details_full.search(resp)

    def generatePersona(friend):
        return {
            "steamID": SteamID.SteamID(friend['m_ulSteamID']),
            "personaName": friend['m_strName'],
            "personaState": PersonaState(friend['m_ePersonaState']),
            "personaStateFlags": PersonaStateFlag(friend.get('m_nPersonaStateFlags') or 0),
            "avatarHash": friend['m_strAvatarHash'],
            "inGame": friend.get('m_bInGame', False),
            "inGameAppID": friend.get('m_nInGameAppID', None),
            "inGameName": friend.get('m_strInGameName', None),
            "nickname": friend.get("m_strNickname", None)
        }

    if matches:
        groups = matches.groups()
        own_persona = generatePersona(json.loads(groups[0]))
        friends = json.loads(groups[1])
        friend_groupings = json.loads(groups[2])

        for friend in friends:
            persona = generatePersona(friend)
            self.chatFriends[str(persona["steamID"])] = persona

        for group_idx, group in list(enumerate(friend_groupings)):
            for idx, member in list(enumerate(group["members"])):
                friend_groupings[group_idx]["members"][
                    idx] = SteamID.SteamID.fromIndividualAccountID(member)

        self.chatFriendGroups = friend_groupings
        self.accountPersona = own_persona
        self.emit('initial', self.chatFriends,
                  self.accountPersona, self.chatFriendGroups)


def chatLogon(self, uiMode="web"):
    """Logs into Steam Web Chat.

    Parameters
    ----------
    uiMode : str, optional
        The login mode to display to friends
        Can be either ``"web"`` or ``"mobile"``

    Returns
    -------
    steamapi.chatState
        An enum value indicating current login state
    """
    if self.chatState == ChatState.LoggingOn or self.chatState == ChatState.LoggedOn:
        return

    logger.info("Requesting chat WebAPI token")
    self.chatState = ChatState.LoggingOn

    err, token = self.getWebApiOauthToken()
    if err:
        fatal = "not authorized" in err

        if not fatal:
            self.chatState = ChatState.LogOnFailed
            self.timer(5.0, self.chatLogon)
        else:
            self.chatState = ChatState.Offline

        self.emit("chatLogOnFailed", err)
        logger.error("Cannot get oauth token: %s", err)

        return self.chatState

    self._chat = {
        "accessToken": token,
        "uiMode": uiMode,
        "pollid": 1,
        "sectimeout": POLL_DEFAULT_TIMEOUT,
        "reconnectTimer": -1
    }

    login = self.session.post(
        APIUrl("ISteamWebUserPresenceOAuth", "Logon"), data={"ui_mode": uiMode, "access_token": token})

    if login.status_code != 200:
        self.chatState = ChatState.LogOnFailed
        logger.error("Error logging into webchat (%s)", login.status_code)
        # self.timer(5.0, self.chatLogon)
        self._chat["reconnectTimer"] = -1
        self._relogWebChat()
        return self.chatState

    login_data = login.json()

    if login_data["error"] != "OK":
        self.chatState = ChatState.LogOnFailed
        logger.error("Error logging into webchat: %s", login_data["error"])
        self.timer(5.0, self.chatLogon)
        return self.chatState

    self._chat.update({
        "umqid": login_data["umqid"],
        "message": login_data["message"]
    })

    self.chatState = ChatState.LoggedOn
    self.emit('chatLoggedOn')
    self.timer(0.5, self._chatPoll, ())
    return ChatState.LoggedOn


def chatMessage(self, recipient, text, type_="saytext"):
    """Sends a message to a specified recipient.

    Parameters
    ----------
    recipient : SteamID.SteamID or str
        The steam ID of the user to send message to.
        If not already an instance of `SteamID.SteamID`, it will be converted into one.
    text : str
        The message to send to the user.
    type_ : str, optional
        The type of message to be sent.
        Known values are:
            - saytext

    Raises
    ------
    Exception
        Raised if you are not logged on.
    """
    if self.chatState != ChatState.LoggedOn:
        raise Exception(
            "Chat must be logged on before messages can be sent")

    if not isinstance(recipient, SteamID.SteamID):
        recipient = SteamID.SteamID(recipient)

    form = {
        "access_token": self._chat.get("accessToken"),
        "steamid_dst": recipient.SteamID64,
        "text": text,
        "type": type_,
        "umqid": self._chat.get("umqid")
    }

    self.session.post(
        APIUrl("ISteamWebUserPresenceOAuth", "Message"), data=form)


def chatLogoff(self):
    """Requests a Logoff from Steam.
    """
    logoff = self.session.post(APIUrl("ISteamWebUserPresenceOAuth", "Logoff"), data={
        "access_token": self._chat.get("accessToken"),
        "umqid": self._chat.get("umqid")
    })

    if logoff.status_code != 200:
        logger.error("Error logging off of chat: %s", logoff.status_code)
        self.timer(1.0, self.chatLogoff)
    else:
        self.emit("chatLoggedOff")
        self._chat = {}
        self.chatFriends = {}
        self.chatState = ChatState.Offline


def getChatHistory(self, steamid):
    """Retrieves the chat history with a given steam ID.

    Parameters
    ----------
    steamid : SteamID.SteamID or str
        The SteamID of which to retrieve chat history of.
        If not already an instance of `SteamID.SteamID`, it will be converted into one.

    Returns
    -------
    list
        A list of parsed history entries in the format::
            [
                {
                    "steamID": `SteamID.SteamID` of the message sender,
                    "timestamp": time which the message was sent,
                    "message": message sent
                },
                ...
            ]
    """
    if not isinstance(steamid, SteamID.SteamID):
        steamid = SteamID.SteamID(steamid)
    form = {"sessionid": self.sessionID}
    resp = self.session.post(CommunityURL(
        "chat", "chatlog") + str(steamid.accountid), data=form)

    if resp.status_code != 200:
        logger.error("Error in loading chatlog: %s", resp.status_code)
        return []

    parsed = []
    body = resp.json()
    for msg in body:
        steamid = SteamID.SteamID.fromIndividualAccountID(msg["m_unAccountID"])
        parsed.append({
            "steamID": steamid,
            "timestamp": msg["m_tsTimestamp"],
            "message": msg["m_strMessage"]
        })

    return parsed


def addFriend(self, steamid):
    """Adds a given user to the friends list via their steamID.

    Parameters
    ----------
    steamid : SteamID.SteamID or str
        The SteamID of which to add to the friends list.
        If not already an instance of `SteamID.SteamID`, it will be converted into one.

    Returns
    -------
    int
        If adding the user was successful, returns 1.
        Other returns are unknown.
        If JSON decoding fails, returns 0.
    """
    if not isinstance(steamid, SteamID.SteamID):
        steamid = SteamID.SteamID(steamid)

    form = {
        "accept_invite": 0,
        "sessionID": self.sessionID,
        "steamid": str(steamid.SteamID64)
    }
    response = self.session.post(CommunityURL(
        'actions', 'AddFriendAjax'), data=form)

    if response.status_code != 200:
        logger.error("Error in adding friend: %s", response.status_code)
        return None

    try:
        body = response.json()
        return body["success"]
    except:
        return 0


def _chatPoll(self):
    """Polls the Steam Web chat API for new events.
    """
    # or not 'umqid' in self._chat
    if self.chatState == ChatState.Offline or not 'umqid' in self._chat:
        self._pollFailed()
        return

    self._chat["pollid"] += 1

    form = {
        "umqid": self._chat["umqid"],
        "message": self._chat["message"],
        "pollid": self._chat["pollid"],
        "sectimeout": self._chat["sectimeout"],
        "secidletime": 0,
        "use_accountids": 1,
        "access_token": self._chat["accessToken"]
    }

    try:
        response = self.session.post(
            APIUrl("ISteamWebUserPresenceOAuth", "Poll"), data=form, timeout=self._chat["sectimeout"] + 5)
    except requests.exceptions.ConnectionError:
        self._pollFailed()
        return

    try:
        body = response.json()
    except:
        body = {}

    if body.get("pollid") != self._chat["pollid"]:
        # discard old responses
        # dunno if this should be possible
        return

    if body.get("message") == "Not Logged On":
        self._relogWebChat()
        return

    if response.status_code != 200 and "error" not in body:
        logger.error("Error in chat poll: %s", response.status_code)
        self._pollFailed()
        return
    elif body["error"] != "OK":
        logger.warning("Error in chat poll: %s", body["error"])
        if body["error"] == "Timeout":
            if "sectimeout" in body and body["sectimeout"] > POLL_DEFAULT_TIMEOUT:
                self._chat["sectimeout"] = body["sectimeout"]

            if self._chat["sectimeout"] < POLL_MAX_TIMEOUT:
                self._chat["sectimeout"] = min(
                    self._chat["sectimeout"] + POLL_SUCCESS_INCREMENT, POLL_MAX_TIMEOUT)
        else:
            self._pollFailed()
            return

    self._chat['message'] = body.get("messagelast", self._chat['message'])

    for message in body.get("messages", []):
        sender = SteamID.SteamID.fromIndividualAccountID(
            message['accountid_from'])

        type_ = message["type"]
        if type_ == "personastate":
            self._chatUpdatePersona(sender)
        elif type_ == "saytext" or type_ == "my_saytext":
            self.emit('chatMessage', sender, message[
                      "text"], type_ == "my_saytext")
        elif type_ == "typing":
            self.emit('chatTyping', sender)
        elif type_ == "personarelationship":
            # what is this?
            print("type == personarelationship:")
            print(message)
        else:
            logger.warning("Unhandled message type: %s", type_)

    self.chatState = ChatState.LoggedOn
    self._chat["consecutivePollFailures"] = 0
    self.timer(0.5, self._chatPoll)
    # self._chatPoll()


def _pollFailed(self):
    """Tracks consecutive poll failures and reconnecting if need be.
    """
    failures = self._chat.get("consecutivePollFailures", 0) + 1
    logger.warning("Poll failed, consecutive failures: %d", failures)
    self._chat["consecutivePollFailures"] = failures

    # set chat to offline while failing
    self.chatState = ChatState.Offline

    if failures == 1:
        if self._chat["sectimeout"] > POLL_DEFAULT_TIMEOUT:
            self._chat["sectimeout"] -= POLL_SUCCESS_INCREMENT

    if failures < 3:
        logger.error(
            "Poll failed, retrying (consecutive failures: %d)", failures)
        self.timer(0.5, self._chatPoll)
    else:
        # too many failures, try to reinitiate login to steam
        logger.error("Poll failed, too many failures (3)")
        self._relogWebChat()


def _relogWebChat(self):
    """Re-initiates login to Steam chat.
    """
    logger.info("Attempting to relogin to web chat")
    if self._chat.setdefault("reconnectTimer", -1) != -1:
        return

    self.chatState = ChatState.Offline
    self._chat["reconnectTimer"] = 5

    if "uiMode" in self._chat:
        self.chatLogon(self._chat.get("uiMode"))
    else:
        self.chatLogon()


def _loadFriendList(self):
    """Loads friend data

    Returns
    -------
    list
        A list of friends in the format::
            [
                {
                    "friend_since": timestamp of when user became friend,
                    "relationship": relationship with friend,
                    "steamid": SteamID64 of friend
                },
                ...
            ]

        ``relationship`` is known to have these values:
            - none
            - blocked
            - pendinginvitee
            - requestrecipient
            - requestinitiator
            - pendinginviter
            - friend
            - ignored
            - ignoredfriend
            - suggestedfriend
    """
    form = {
        "access_token": self.oAuthToken,
        "steamid": str(self.steamID)
    }

    response = self.session.get(
        APIUrl("ISteamUserOAuth", "GetFriendList", version="0001"), params=form)

    if response.status_code != 200:
        if response.status_code == 401: # Client Error: Unauthorized
            self._relogWebChat()
        logger.error("Load friends error: %s", response.status_code)
        self.timer(2.0, self._loadFriendList)
        return None

    body = response.json()
    if "friends" in body:
        return body["friends"]

    return []


def _chatUpdatePersona(self, steamID):
    """Retrieves new persona data for when persona event is received.

    Parameters
    ----------
    steamID : `SteamID.SteamID`
        The SteamID of the user to update persona of.
    """
    accnum = steamID.accountid
    response = self.session.get(
        CommunityURL("chat", "friendstate") + str(accnum))

    if response.status_code != 200:
        if response.status_code == 401: # Client Error: Unauthorized
            self._relogWebChat()
        logger.error("Chat update persona error: %s", response.status_code)
        self.timer(2.0, self._chatUpdatePersona, (steamID,))
        return None

    if str(steamID) in self.chatFriends:
        old_persona = self.chatFriends[str(steamID)]
        steamID = old_persona["steamID"]
    else:
        old_persona = {}

    body = response.json()

    persona = {
        "steamID": steamID,
        "personaName": body['m_strName'],
        "personaState": PersonaState(body['m_ePersonaState']),
        "personaStateFlags": PersonaStateFlag(body.get('m_nPersonaStateFlags') or 0),
        "avatarHash": body['m_strAvatarHash'],
        "inGame": body.get('m_bInGame', False),
        "inGameAppID": body.get('m_nInGameAppID', None),
        "inGameName": body.get('m_strInGameName', None),
        "nickname": old_persona.get("nickname", None)
    }

    self.emit(
        'chatPersonaState', steamID, persona, old_persona)
    self.chatFriends[str(steamID)] = persona
