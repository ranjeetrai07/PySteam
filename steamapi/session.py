from .utils import emit
import requests
import re
import logging
logger = logging.getLogger(__name__)

session = requests.Session()

_mobileHeaders = {
    "X-Requested-With": "com.valvesoftware.android.steam.community",
    "referer": "https://steamcommunity.com/mobilelogin?oauth_client_id=DE45CD61&oauth_scope=read_profile%20write_profile%20read_client%20write_client",
    "user-agent": "Mozilla/5.0 (Linux; U; Android 4.1.1; en-us; Google Nexus 4 - 4.1.1 - API 16 - 768x1280 Build/JRO03S) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
    "accept": "text/javascript, text/html, application/xml, text/xml, */*"
}
session.headers = _mobileHeaders
session.cookies.set("Steam_Language", "english")
session.cookies.set("timezoneOffset", "0,0")
session.cookies.set("mobileClientVersion", "0 (2.1.3)")
session.cookies.set("mobileClient", "android")


def validate_response(r, *args, **kwargs):
    """Checks for Steam's definitions of errors.
    """
    check_http_error(r)
    check_community_error(r)


def check_http_error(response):
    """Checks for Steam's definition of an error.
    """
    if response.status_code >= 300 and response.status_code <= 399 and "/login" in response.headers["location"]:
        emit('session_expired')
        return True

    if response.status_code >= 400:
        return True

    return False


def check_community_error(response):
    """Checks for Steam's definition of an community error.
    """
    body = response.text
    if re.search(r"<h1>Sorry!<\/h1>", body):
        return True

    if re.search(r"g_steamID = false;", body) and re.search(r"<h1>Sign In<\/h1>", body):
        emit('session_expired')
        return True

    return False


session.hooks = dict(response=validate_response)
