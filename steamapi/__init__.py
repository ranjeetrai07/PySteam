from __future__ import unicode_literals
from builtins import bytes
import base64
import json
import re
import pickle
import os
import requests
from io import open
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from .steamid import SteamID
from .session import session
from .chat import Chat
from . import utils
from . import enums

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class steamapi(object):
    """Provides a Python interface to the Steam Web API
    """

    event = utils.emitter
    chat = Chat()
    session = session

    from .profile import setup_profile, edit_profile, edit_privacy_settings, upload_avatar

    def __init__(self):
        self.oauth_client_id = "DE45CD61"
        self._captchaGid = -1

        # cache to store login credentials for two-factor usage
        self._cache = {}

        self.steam_id = SteamID()
        self.oauth_token = ""
        self._matchine_auth = ""
        self.steamguard = "||"

    def save_cookies(self, filename):
        """Saves session cookies to a given filename.

        Parameters
        ----------
        filename : str
            The filename to save cookies to.
        """
        try:
            with open(filename, 'wb') as f:
                f.truncate()
                pickle.dump(session.cookies._cookies, f)
        except:
            return False

        return True

    def load_cookies(self, filename):
        """
        Loads session cookies from a given filename.

        Parameters
        ----------
        filename : str
            The filename to load cookies from.
        """
        if not os.path.isfile(filename):
            return False

        with open(filename, 'rb') as f:
            cookies = pickle.load(f)
            if cookies:
                jar = requests.cookies.RequestsCookieJar()
                jar._cookies = cookies
                session.cookies = jar
            else:
                return False

        return True

    def login(self, **details):
        """Initiates login for Steam community.

        Parameters
        ----------
        **details
            Can have any of the following values:
                - username: str
                - password: str
                - captcha: str
                - steamguard: str
                - twofactor: str


        Returns
        -------
        ``steamapi.enums.LoginStatus``
            A value from the LoginStatus enum indicating result.

        Raises
        ------
        Exception
            Raised when steam dologin returns a non-ok error
        """
        rsakey = session.post(utils.url_community("login", "getrsakey"), data={
            "username": details["username"]})

        if not rsakey.ok:
            rsakey.raise_for_status()
            return None

        rsakey = rsakey.json()

        mod = int(rsakey["publickey_mod"], 16)
        exp = int(rsakey["publickey_exp"], 16)
        rsa_key = RSA.construct((mod, exp))
        # rsa = PKCS1_v1_5.PKCS115_Cipher(rsa_key)
        rsa = PKCS1_v1_5.new(rsa_key)

        form = {
            "captcha_text": details.get("captcha", ""),
            "captchagid": self._captchaGid,
            "emailauth": details.get('steamguard', ""),
            "emailsteamid": "",
            "password": base64.b64encode(rsa.encrypt(bytes(details["password"], 'utf8'))),
            "remember_login": "true",
            "rsatimestamp": rsakey["timestamp"],
            "twofactorcode": details.get('twofactor', ""),
            "username": details['username'],
            "oauth_client_id": self.oauth_client_id,
            "oauth_scope": "read_profile write_profile read_client write_client",
            "loginfriendlyname": "#login_emailauth_friendlyname_mobile"
        }

        try:
            login = session.post(
                utils.url_community("login", "dologin"), data=form).json()
        except requests.exceptions.ConnectionError as e:
            logger.error(e)
            return enums.LoginStatus.LoginFailed

        if "success" not in login:
            logger.error("Malformed /login/dologin JSON response")
            return enums.LoginStatus.LoginFailed

        # cache details so they can be used for `steam.retry`
        self._cache = details

        if not login["success"] and login.get("emailauth_needed"):
            return enums.LoginStatus.SteamGuard
        elif not login["success"] and login.get("requires_twofactor"):
            return enums.LoginStatus.TwoFactor
        elif not login["success"] and login.get("captcha_needed"):
            print("Captcha URL: https://steamcommunity.com/public/captcha.php?gid=" +
                  login["captcha_gid"])
            self._captchaGid = login["captcha_gid"]
            return enums.LoginStatus.Captcha
        elif not login["success"]:
            raise Exception(login.get("message", "Unknown error"))
        else:
            session_id = utils.generate_session_id()
            oAuth = json.loads(login["oauth"])
            session.cookies.set("sessionid", str(session_id))
            self.session_id = str(session_id)

            self.steam_id = SteamID(oAuth["steamid"])
            self.oauth_token = oAuth["oauth_token"]
            self._matchine_auth = session.cookies.get(
                "steamMachineAuth" + str(self.steam_id), '')

            # clear cached details if login succeeds
            self._cache = {}
            self.steamguard = str(self.steam_id) + "||" + self._matchine_auth

            return enums.LoginStatus.LoginSuccessful

        return enums.LoginStatus.LoginFailed

    def retry(self, **details):
        """Retries a previously failed login attempt.

        Commonly used to submit a SteamGuard or Mobile Authenticator code.

        Parameters
        ----------
        **details
            Description
        """
        deets = self._cache.copy()
        deets.update(details)
        return self.login(**deets)

    def oauth_login(self, steamguard, token):
        """Allows password-less login to steam using OAuth tokens.

        Parameters
        ----------
        steamguard : str
            A previous saved steamguard string.
            Can be obtained via the `steamguard` property.
        token : str
            A previous saved OAuth token.
            Can be obtained via the `oauth_token` property.
        """
        steamguard = steamguard.split('||')
        steam_id = SteamID(steamguard[0])

        form = {"access_token": token}
        login = session.post(
            utils.url_api("IMobileAuthService", "GetWGToken"), data=form)

        if not login:
            resp = {}
        else:
            resp = login.json().get('response', {})

        if 'token' not in resp or 'token_secure' not in resp:
            logger.error("Error logging in with OAuth: Malformed response")
            return enums.LoginStatus.LoginFailed

        sid = str(steam_id.as_64)
        session.cookies.set('steamLogin', sid + '||' + resp['token'])
        session.cookies.set(
            'steamLoginSecure', sid + '||' + resp['token_secure'])
        if steamguard[1]:
            session.cookies.set('steamMachineAuth' + sid, steamguard[1])
        session.cookies.set('sessionid', utils.get_session_id())

        return enums.LoginStatus.LoginSuccessful

    def unlock_parental(self, pin):
        """Unlocks an account locked via parental controls.

        Parameters
        ----------
        pin : str
            The pin used to unlock.

        Returns
        -------
        bool
            True if unlock succeeds, False otherwise.
        """
        unlock = session.post(
            utils.url_community('parental', 'ajaxunlock'), data={"pin": pin})

        if not unlock:
            logger.error("Error unlocking parental with pin: Unknown error")
            return False

        if unlock.status_code != 200:
            logger.error('HTTP error %s', unlock.status_code)
            return False

        resp = unlock.json()
        if not resp:
            logger.error("Error unlocking parental with pin: Invalid response")
            return False

        if not resp.get('success'):
            logger.error("Error unlocking parental with pin: Incorrect PIN")
            return False

        return True

    def get_notifications(self):
        """Gets the count of your current notifications.

        Returns
        -------
        dict
            A dictionary resembling the following structure::

                {
                    "comments": 0,
                    "items": 0,
                    "invites": 0,
                    "gifts": 0,
                    "chat": 2,
                    "trades": 0
                }

        """
        notifications = session.get(
            utils.url_community('actions', 'GetNotificationCounts'))

        if not notifications:
            logger.error("Error retrieving notifications")
            return {}

        resp = notifications.json()

        items = {
            "comments": 4,
            "items": 5,
            "invites": 6,
            "gifts": 8,
            "chat": 9,
            "trades": 1
        }

        notifs = {}

        for item, key in list(items.items()):
            notifs[item] = resp['notifications'][str(key)]

        return notifs

    def reset_item_notifications(self):
        """Resets the item notification count.

        Returns
        -------
        bool
            True if request succeeded, False otherwise.
        """
        res = session.get(utils.url_community('my', 'inventory'))
        if res:
            return True

        return False

    def add_friend(self, steam_id):
        """Adds a given user to the friends list via their steam ID.

        Parameters
        ----------
        steam_id : `steamapi.SteamID`` or str
            The Steam ID of which to add to the friends list.
            If not already an instance of `steamapi.SteamID``, it will be converted into one.

        Returns
        -------
        int
            If adding the user was successful, returns 1.
            Other returns are unknown.
            If JSON decoding fails, returns 0.
        """
        if not isinstance(steam_id, SteamID):
            steam_id = SteamID(steam_id)

        form = {
            "accept_invite": 0,
            "sessionID": utils.get_session_id(),
            "steamid": str(steam_id.as_64)
        }
        response = session.post(utils.url_community(
            'actions', 'AddFriendAjax'), data=form)

        if not response.ok:
            logger.error("Error in adding friend: %s", response.status_code)
            return None

        try:
            body = response.json()
            return body["success"]
        except:
            return 0

    @property
    def logged_in(self):
        """Checks whether instance is logged into the Steam community.

        Returns
        -------
        ``steamapi.enums.LoggedIn``
            A value from the LoggedIn enum indicating status.
        """
        resp = session.get(utils.url_community(
            'my', ''), allow_redirects=False)

        if resp.status_code != 302 and resp.status_code != 403:
            logger.error('HTTP error %s', resp.status_code)
            return enums.LoggedIn.GeneralError

        if resp.status_code == 403:
            # needs a PIN to unlock
            return enums.LoggedIn.FamilyView

        id_match = re.compile(
            r'steamcommunity\.com(\/(id|profiles)\/[^\/]+)\/?')

        if id_match.search(resp.headers['location']):
            return enums.LoggedIn.LoggedIn

        return enums.LoggedIn.GeneralError
