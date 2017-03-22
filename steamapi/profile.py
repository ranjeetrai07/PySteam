from __future__ import unicode_literals
from .session import session
from . import utils
from . import enums
from pyquery import PyQuery as pq
import logging
logger = logging.getLogger(__name__)


@staticmethod
def setup_profile():
    """Initiates a new Steam Profile
    """
    resp = session.get(utils.url_community(
        'profiles', str(utils.get_steam_id())) + 'edit?welcomed=1')
    return resp and resp.ok


@staticmethod
def edit_profile(new_values=None):
    """Updates your Steam profile information.

    Current values are returned if `new_values` is not supplied.

    Supported values for editing are
    --------------------------------
    - `personaName`
    - `real_name`
    - `country`
    - `state`
    - `city`
    - `customURL`
    - `summary`
    - `profile_background`
    - `primary_group_steamid`

    Parameters
    ----------
    new_values : dict, optional
        Dict with editable values, for example::

            {
                'personaName': 'new display name',
                'summary': 'coolest guy ever'
            }

    Returns
    -------
    tuple of (error: str or None, dict)
        `(error, current values)` if `new_values` is not provided,
        else `(error, new values)`.
    """
    def editables(values):
        valid = ['personaName', 'real_name', 'country', 'state', 'city',
                 'customURL', 'summary', 'profile_background', 'primary_group_steamid']

        return {k: v for k, v in list(values.items()) if k in valid}

    def parseForValues(doc):
        values = {}

        all_inputs = doc('#editForm :input').filter(
            lambda i, this: this.tag != "button")
        # visible = all_inputs.filter("[type!='hidden']")
        without_file = all_inputs.filter("[type!='file']")

        for inp in without_file:
            values[inp.name] = inp.value

        return values

    edit_url = utils.url_community(
        'profiles', str(utils.get_steam_id())) + 'edit'
    doc = pq(session.get(edit_url).text)

    values = parseForValues(doc)

    if not new_values:
        return (None, editables(values))
    else:
        values.update(new_values)
        update_resp = pq(session.post(edit_url, data=values).text)
        values = parseForValues(update_resp)
        error = update_resp('#errorText .formRowFields')
        if error:
            return (error.text.strip(), editables(values))

        return (None, editables(values))


@staticmethod
def edit_privacy_settings(new_values=None):
    """Updates your Steam privacy settings.

    Current values are returned if `new_values` is not supplied.

    Supported values for editing are
    --------------------------------
    - `privacySetting`
    - `commentSetting`
    - `inventoryPrivacySetting`
    - `inventoryGiftPrivacy`

    Parameters
    ----------
    new_values : dict, optional
        Dict with editable values, for example::

            {
                'personaName': 'new display name',
                'summary': 'coolest guy ever'
            }

    Returns
    -------
    tuple of (error: str or None, dict)
        `(error, current values)` if `new_values` is not provided,
        else `(error, new values)`.
    """
    def editables(values):
        valid = ['privacySetting', 'commentSetting',
                 'inventoryPrivacySetting', 'inventoryGiftPrivacy']

        return {k: v for k, v in list(values.items()) if k in valid}

    def parseForValues(doc):
        all_inputs = doc('#editForm :input').filter(
            lambda i, this: this.tag != "button")

        values = {inp.name: inp.value for inp in all_inputs}

        for inp in doc('#editForm input:checked'):
            values[inp.name] = inp.value
            if inp.name in ['privacySetting', 'inventoryPrivacySetting']:
                values[inp.name] = enums.PrivacyState(int(inp.value))
            if inp.name == 'commentSetting':
                values[inp.name] = enums.CommentPrivacyState(inp.value)

        if values['inventoryGiftPrivacy'] is not None:
            values['inventoryGiftPrivacy'] = bool(
                int(values['inventoryGiftPrivacy']))
        else:
            values['inventoryGiftPrivacy'] = False

        return values

    edit_url = utils.url_community('profiles', str(
        utils.get_steam_id())) + 'edit/settings'
    doc = pq(session.get(edit_url).text)
    values = parseForValues(doc)

    if not new_values:
        return (None, editables(values))
    else:
        values.update(new_values)
        for k, v in list(editables(values).items()):
            if k == 'inventoryGiftPrivacy':
                values[k] = int(v)
            else:
                values[k] = v.value

        resp = session.post(edit_url, data=values)
        update_resp = pq(resp.text)
        values = parseForValues(update_resp)
        error = update_resp('#errorText .formRowFields')
        if error:
            return (error.text.strip(), editables(values))

        return (None, editables(values))


@staticmethod
def upload_avatar(image):
    """Sets the current account's avatar on Steam.

    Parameters
    ----------
    image : file
        File-like object, in binary mode.
    """
    data = {
        'MAX_FILE_SIZE': 1048576,
        'type': 'player_avatar_image',
        'sId': str(utils.get_steam_id()),
        'sessionid': utils.get_session_id(),
        'doSub': 1,
        'json': 1
    }

    files = {'avatar': image}
    resp = session.post(utils.url_community(
        'actions', 'FileUploader'), files=files, data=data)

    if not resp.ok:
        logger.error('Avatar upload: HTTP error %s', resp.status_code)
        return

    try:
        body = resp.json()
    except:
        body = {}

    if not body or not body.get('success'):
        logger.error('Avatar upload: Malformed response')

    if not body.get('success') and body.get('message'):
        logger.error('Avatar upload: %s', body['message'])

    return body
