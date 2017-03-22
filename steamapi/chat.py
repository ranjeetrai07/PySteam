from __future__ import unicode_literals
import requests
import re
import json
from munch import Munch
from .steamid import SteamID
from .session import session, check_http_error
from . import utils
from . import enums
import logging
logger = logging.getLogger(__name__)

# chat constants taken from chat.js
POLL_DEFAULT_TIMEOUT = 20
POLL_SUCCESS_INCREMENT = 5
POLL_MAX_TIMEOUT = 120


def get_chat_oauth_token(return_response=False):
    """Retrieves necessary OAuth token for Steam Web chat.

    Parameters
    ----------
    return_response : bool, optional
        If True, returns the text response from get
        request for later processing.

    Returns
    -------
    tuple of (error: str or None, token: str or None)
        OAuth token to use for chat authentication.
    """
    ret = ()
    resp = session.get("https://steamcommunity.com/chat")
    if check_http_error(resp):
        ret = ("HTTP Error", None)

    token = re.compile(r'"([0-9a-f]{32})" \);')
    matches = token.search(resp.text)
    if matches:
        ret = (None, matches.groups()[0])

    if ret is ():
        ret = ("Malformed Response", None)

    if return_response:
        if hasattr(resp, "text"):
            ret += (resp.text,)
        else:
            ret += (None,)

    return ret


class Chat(object):
    """Allows for Steam Chat WebAPI communication.

    Attributes
    ----------
    access_token : str
        Chat OAuth token
    account_persona : dict
        Persona for logged in user
    friend_groups : list
        Friends list groupings
    friends : list
        Friends list
    state : ``steamapi.enums.chatState``
        Logged in state
    ui_mode : str
        UI mode to report to Steam
        Can be either `"mobile"` or `"web"`
    """

    def __init__(self):
        self._restore_defaults()

    def _restore_defaults(self):
        """Restores (and sets) default values for chat.
        """
        # chat connection attributes
        self.access_token = ""
        self.ui_mode = "web"
        self._poll_id = 1
        self._sec_timeout = POLL_DEFAULT_TIMEOUT
        self._reconnect_timer = -1
        self._umqid = ""
        self._message = 0
        self._session_id = utils.get_session_id()
        self._consecutive_poll_failures = 0
        self._logged_out_forcefully = False

        # chat interaction attributes
        self.account_persona = {}
        self.friends = {}
        self.friend_groups = []
        self.state = enums.ChatState.Offline

    def _parse_initial_details(self, resp):
        """Parses the chat page for the initial persona details.

        The chat page is parsed for:
            - Your own persona details
              This is needed because the API is inconsistent and may or may not
              include yourself in the friend persona list.
              Stored as `self.account_persona`
            - All friend persona details
              Stored as `self.friends`
            - Friends list groupings
              Stored as `self.friend_groups`

        Parameters
        ----------
        resp : str
            The content of a page which has a call to CWebChat in its embedded script.
            (namely https://steamcommunity.com/chat/)
        """
        details_full = re.compile(r'WebAPI, (\{.*\}), (\[.*\]), (\[.*\]) \);')
        matches = details_full.search(resp)

        def generate_persona(friend):
            return Munch({
                "steam_id": SteamID(friend['m_ulSteamID']),
                "name": friend['m_strName'],
                "state": enums.PersonaState(friend.get('m_ePersonaState', 0)),
                "state_flags": enums.PersonaStateFlag(friend.get('m_nPersonaStateFlags') or 0),
                "avatar_hash": friend['m_strAvatarHash'],
                "ingame": friend.get('m_bInGame', False),
                "ingame_app_id": friend.get('m_nInGameAppID', None),
                "ingame_name": friend.get('m_strInGameName', None),
                "nickname": friend.get("m_strNickname", None)
            })

        if matches:
            groups = matches.groups()
            own_persona = generate_persona(json.loads(groups[0]))
            friends = json.loads(groups[1])
            friend_groups = json.loads(groups[2])

            for friend in friends:
                persona = generate_persona(friend)
                self.friends[str(persona.steam_id)] = persona

            for group_idx, group in list(enumerate(friend_groups)):
                for idx, member in list(enumerate(group["members"])):
                    friend_groups[group_idx]["members"][
                        idx] = SteamID.from_account_id(member)

            self.friend_groups = friend_groups
            self.account_persona = own_persona
            utils.emit('initial', self.friends,
                       self.account_persona, self.friend_groups)

    def login(self, ui_mode="web"):
        """Initiates login for Steam web chat.

        Parameters
        ----------
        ui_mode : str, optional
            The login mode to display to friends
            Can be either ``"web"`` or ``"mobile"``

        Returns
        -------
        ``steamapi.enums.chatState``
            An enum value indicating current login state
        """
        self._restore_defaults()
        if self.state is enums.ChatState.LoggingOn or self.state is enums.ChatState.LoggedOn:
            logger.warning("Trying to login to chat when already logged in...")
            return

        logger.info("Requesting chat WebAPI token")
        self.state = enums.ChatState.LoggingOn

        err, token, resp = get_chat_oauth_token(return_response=True)
        if err:
            fatal = "not authorized" in err

            if not fatal:
                self.state = enums.ChatState.LogOnFailed
                utils.timer(5.0, self.login)
            else:
                self.state = enums.ChatState.Offline

            utils.emit("chat_logon_failed", err)
            logger.error("Cannot get oauth token: %s", err)

            return self.state

        self._parse_initial_details(resp)

        self.access_token = token
        self.ui_mode = ui_mode
        self._poll_id = 1
        self._sec_timeout = POLL_DEFAULT_TIMEOUT
        self._reconnect_timer = -1

        login = session.post(
            utils.url_api("ISteamWebUserPresenceOAuth", "Logon"), data={"ui_mode": ui_mode, "access_token": token})

        if not login.ok:
            self.state = enums.ChatState.LogOnFailed
            logger.error("Error logging into webchat (%s)", login.status_code)
            self._reconnect_timer = -1
            self._relog_chat()
            return self.state

        login_data = login.json()

        if login_data["error"] != "OK":
            self.state = enums.ChatState.LogOnFailed
            logger.error("Error logging into webchat: %s", login_data["error"])
            self._relog_chat()
            return self.state

        self._umqid = login_data["umqid"]
        self._message = login_data["message"]

        self.state = enums.ChatState.LoggedOn
        utils.emit('chat_logged_on')
        utils.timer(0.5, self._poll, ())
        return self.state

    def send_message(self, recipient, text, type_="saytext"):
        """Sends a message to a specified recipient.

        Parameters
        ----------
        recipient : ``steamapi.SteamID`` or str
            The steam ID of the user to send message to.
            If not already an instance of ``steamapi.SteamID``, it will be converted into one.
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
        if self.state is not enums.ChatState.LoggedOn:
            raise Exception(
                "Chat must be logged on before messages can be sent")

        if not isinstance(recipient, SteamID):
            recipient = SteamID(recipient)

        form = {
            "access_token": self.access_token,
            "steamid_dst": recipient.as_64,
            "text": text,
            "type": type_,
            "umqid": self._umqid
        }

        session.post(utils.url_api(
            "ISteamWebUserPresenceOAuth", "Message"), data=form)

    def logout(self):
        """Requests a log out of Steam chat.
        """
        logoff = session.post(utils.url_api("ISteamWebUserPresenceOAuth", "Logoff"), data={
            "access_token": self.access_token,
            "umqid": self._umqid
        })

        if not logoff.ok:
            logger.error("Error logging out of chat: %s", logoff.status_code)
            utils.timer(2.0, self.logout)
        else:
            utils.emit("chat_logged_out")

            # reset all variables to default
            self._restore_defaults()
            self._logged_out_forcefully = True

    def get_chat_history(self, steam_id):
        """Retrieves the chat history with a given steam ID.

        Parameters
        ----------
        steam_id : ``steamapi.SteamID`` or str
            The Steam ID of which to retrieve chat history of.
            If not already an instance of ``steamapi.SteamID``, it will be converted into one.

        Returns
        -------
        list
            A list of parsed history entries in the format::

                [
                    {
                        "steamID": ``steamapi.SteamID`` of the message sender,
                        "timestamp": time which the message was sent,
                        "message": message sent
                    },
                    ...
                ]
        """
        if not isinstance(steam_id, SteamID):
            steam_id = SteamID(steam_id)

        form = {"sessionid": utils.get_session_id()}
        resp = session.post(utils.url_community(
            "chat", "chatlog") + str(steam_id.accountid), data=form)

        if not resp.ok:
            logger.error("Error in loading chatlog: %s", resp.status_code)
            return []

        parsed = []
        body = resp.json()
        for msg in body:
            steam_id = SteamID.from_account_id(msg["m_unAccountID"])
            parsed.append(Munch({
                "steam_id": steam_id,
                "timestamp": msg["m_tsTimestamp"],
                "message": msg["m_strMessage"]
            }))

        return parsed

    def _poll(self):
        """Polls the Steam Web chat API for new events.
        """
        if self.state is enums.ChatState.Offline or self._umqid is "":
            self._poll_failed()
            return

        self._poll_id += 1

        form = {
            "umqid": self._umqid,
            "message": self._message,
            "pollid": self._poll_id,
            "sectimeout": self._sec_timeout,
            "secidletime": 0,
            "use_accountids": 1,
            "access_token": self.access_token
        }

        try:
            response = session.post(
                utils.url_api("ISteamWebUserPresenceOAuth", "Poll"), data=form, timeout=self._sec_timeout + 5)
        except requests.exceptions.ConnectionError:
            self._poll_failed()
            return

        try:
            body = response.json()
        except:
            body = {}

        if body.get("pollid") != self._poll_id:
            # discard old responses
            # dunno if this should be possible
            return

        if body.get("message") == "Not Logged On":
            self._relog_chat()
            return

        if not response.ok and "error" not in body:
            logger.error("Error in chat poll: %s", response.status_code)
            self._poll_failed()
            return
        elif body["error"] != "OK":
            if body["error"] == "Timeout":
                logger.debug("Timeout in chat poll: %s", body["error"])
                if "sectimeout" in body and body["sectimeout"] > POLL_DEFAULT_TIMEOUT:
                    self._sec_timeout = body["sectimeout"]

                if self._sec_timeout < POLL_MAX_TIMEOUT:
                    self._sec_timeout = min(
                        self._sec_timeout + POLL_SUCCESS_INCREMENT, POLL_MAX_TIMEOUT)
            else:
                logger.error("Error in chat poll: %s", body["error"])
                self._poll_failed()
                return

        self._message = body.get("messagelast", self._message)

        for message in body.get("messages", []):
            sender = SteamID.from_account_id(message['accountid_from'])

            type_ = message["type"]
            if type_ == "personastate":
                self._update_persona(sender)
            elif type_ == "saytext" or type_ == "my_saytext":
                utils.emit('chat_message', sender,
                           message["text"], type_ == "my_saytext")
            elif type_ == "typing":
                utils.emit('chat_typing', sender)
            # elif type_ == "personarelationship":
            #     print("type == personarelationship:")
            #     print(message)
            else:
                logger.warning("Unhandled message type: %s", type_)

        self.state = enums.ChatState.LoggedOn
        self._consecutive_poll_failures = 0
        utils.timer(0.5, self._poll)

    def _poll_failed(self):
        """Tracks consecutive poll failures and reconnects if need be.
        """
        failures = self._consecutive_poll_failures + 1
        logger.warning("Poll failed, consecutive failures: %d", failures)
        self._consecutive_poll_failures = failures

        # set chat to offline while failing
        self.state = enums.ChatState.Offline

        if failures == 1:
            if self._sec_timeout > POLL_DEFAULT_TIMEOUT:
                self._sec_timeout -= POLL_SUCCESS_INCREMENT

        if failures < 3:
            logger.error(
                "Poll failed, retrying (consecutive failures: %d)", failures)
            utils.timer(0.5, self._poll)
        else:
            # too many failures, try to reinitiate login to steam
            logger.error("Poll failed, too many failures (3)")
            self._relog_chat()

    def _relog_chat(self):
        """Re-initiates login to Steam chat.
        """
        logger.info("Attempting to relogin to web chat")
        if not self._logged_out_forcefully and self._reconnect_timer == -1:
            self.state = enums.ChatState.Offline
            self._reconnect_timer = 5

            self.login(self.ui_mode)

    def get_friends_list(self):
        """Loads friend data

        Returns
        -------
        list
            A list of friends in the format::
                [
                    {
                        "friend_since": timestamp of when user became friend,
                        "relationship": relationship with friend,
                        "steam_id": ``steamapi.SteamID`` of friend
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
            "access_token": self.access_token,
            "umqid": self._umqid,
            "steamid": str(utils.get_steam_id())
        }

        try:
            response = session.get(
                utils.url_api("ISteamUserOAuth", "GetFriendList", version="0001")[:-1], params=form)
        except requests.exceptions.ConnectionError:
            return []

        if not response.ok:
            logger.error("Load friends error: %s", response.status_code)
            return []

        body = response.json()
        parsed = []

        if "friends" in body:
            for friend in body["friends"]:
                parsed.append(Munch({
                    "friend_since": friend["friend_since"],
                    "relationship": friend["relationship"],
                    "steam_id": SteamID(friend["steam_id"])
                }))

            return parsed

        return []

    def _update_persona(self, steam_id):
        """Retrieves new persona data for when persona event is received.

        Parameters
        ----------
        steam_id : ``steamapi.SteamID`` or str
            The Steam ID of the user to update persona of.
            If not already an instance of ``steamapi.SteamID``, it will be converted into one.
        """
        if not isinstance(steam_id, SteamID):
            steam_id = SteamID(steam_id)

        response = session.get(
            utils.url_community("chat", "friendstate") + str(steam_id.accountid))

        if not response.ok:
            logger.error("Chat update persona error: %s", response.status_code)
            return

        if str(steam_id) in self.friends:
            old_persona = self.friends[str(steam_id)]
            steam_id = old_persona.steam_id
        else:
            old_persona = {}

        body = response.json()

        persona = Munch({
            "steam_id": steam_id,
            "name": body['m_strName'],
            "state": enums.PersonaState(body.get('m_ePersonaState', 0)),
            "state_flags": enums.PersonaStateFlag(body.get('m_nPersonaStateFlags') or 0),
            "avatar_hash": body['m_strAvatarHash'],
            "ingame": body.get('m_bInGame', False),
            "ingame_app_id": body.get('m_nInGameAppID', None),
            "ingame_name": body.get('m_strInGameName', None),
            "nickname": old_persona.get("nickname", None)
        })

        utils.emit('chat_persona_state', steam_id, persona, old_persona)
        self.friends[str(steam_id)] = persona

    @property
    def logged_in(self):
        """Checks whether instance is logged into the Steam chat.

        Returns
        -------
        ``steamapi.enums.LoggedIn``
            A value from the LoggedIn enum indicating status.
        """
        resp = session.get(utils.url_community(
            'chat', ''), allow_redirects=False)

        if resp.status_code == 302 or resp.status_code == 403:
            logger.error('HTTP error %s', resp.status_code)
            return enums.LoggedIn.GeneralError

        details_full = re.compile(r'WebAPI, (\{.*\}), (\[.*\]), (\[.*\]) \);')
        matches = details_full.search(resp.text)
        if matches:
            return enums.LoggedIn.LoggedIn

        return enums.LoggedIn.GeneralError
