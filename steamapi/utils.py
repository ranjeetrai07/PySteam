from Crypto import Random
import codecs
from pyee import EventEmitter
from threading import Timer
from .steamid import SteamID

emitter = EventEmitter()


def emit(event, *data):
    """The default emit implementation.

    This is normally intended to be replaced should this library
    need to be used in specific event cases, such as Qt.

    Parameters
    ----------
    event : str
        The event to be emitted.
    *data
        The data to be passed to the callback
    """
    emitter.emit(event, *data)


def timer(delay, func, args=()):
    """The default timer implementation.

    This is normally intended to be replaced should this library
    need to be used in specific timing cases, such as Qt.

    Parameters
    ----------
    delay : int or float
        How many seconds to wait before calling ``func``.
    func : function
        The function to call when <delay> seconds pass.
    args : tuple, optional
        The arguments to pass to ``func``.
    """
    timer = Timer(delay, func, args)
    timer.daemon = True
    timer.start()


def url_community(namespace, method):
    """Generates a full Steam community url.

    Parameters
    ----------
    namespace : str
        The community namespace. (login, id, profile, etc..)
    method : str
        The endpoint for that namespace. (dologin, etc...)

    Returns
    -------
    str
        Full Steam URL
    """
    return 'https://steamcommunity.com/{namespace}/{method}/'.format(namespace=namespace, method=method)


def url_api(namespace, method, version="1"):
    """Generates a full Steam API url.

    Parameters
    ----------
    namespace : str
        The API namespace. (login, id, profile, etc..)
    method : str
        The endpoint for that namespace. (dologin, etc...)
    version : str, optional
        The version of the API call to use. Defaults to 1.

    Returns
    -------
    str
        Full Steam URL
    """
    return 'https://api.steampowered.com/{namespace}/{method}/v{version}/'.format(namespace=namespace, method=method, version=version)


def generate_session_id():
    """Generates a random session ID for Steam.

    Returns
    -------
    str
        A random 12 byte hex string.
    """
    return codecs.getencoder('hex')(Random.get_random_bytes(12))[0].decode('utf-8')


def get_session_id():
    """Gets the current session ID for Steam.

    Returns
    -------
    str
        Current session ID if it exists, else a new session ID.
    """
    from .session import session
    return session.cookies.get('sessionid', generate_session_id())


def get_steam_id():
    """Gets the currently logged in steam ID.

    Returns
    -------
    ``steamapi.SteamID``
        The currently logged in steam ID.
    """
    from .session import session
    return SteamID(session.cookies.get('steamLogin', '%7C%7C').split("%7C%7C")[0])


def url_avatar(hashed, quality='full'):
    """Provides the full URL for a steam avatar.

    Parameters
    ----------
    hashed : str
        The avatar hash.
    quality : str, optional
        The quality to use; may be any of:

            - icon
            - medium
            - full

    Returns
    -------
    str
        The full URL of the steam avatar.
    """
    if quality == 'icon' or quality == '':
        quality = ''
    else:
        quality = '_' + quality

    if hashed == ('0' * 40):
        # the user has no avatar, provide the steam default instead
        hashed = 'fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb'

    # first two characters of the hash are used as a tag
    tag = hashed[:2]
    return 'http://cdn.akamai.steamstatic.com/steamcommunity/public/images/avatars/{tag}/{hash}{quality}.jpg'.format(
        tag=tag, hash=hashed, quality=quality)


def dict_diff(a, b):
    """Returns the difference between two dictionaries.

    Parameters
    ----------
    a : dict
        The dictionary to prefer different results from.
    b : dict
        The dictionary to compare against.

    Returns
    -------
    dict
        A dictionary with only the different keys: values.
    """
    diff = {}

    for key in list(a.keys()):
        if key in b:
            if b[key] != a[key]:
                diff[key] = a[key]
        else:
            diff[key] = a[key]

    return diff
