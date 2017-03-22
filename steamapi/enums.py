from enum import Enum, IntEnum, unique


class StrEnum(str, Enum):
    pass


@unique
class LoginStatus(IntEnum):
    """Possible login states.
    """
    Waiting, LoginFailed, LoginSuccessful, SteamGuard, TwoFactor, Captcha = list(range(
        6))


@unique
class LoggedIn(IntEnum):
    """Possible logged in states.
    """
    GeneralError = 0
    LoggedIn = 1
    FamilyView = 2


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


@unique
class PrivacyState(IntEnum):
    Private, FriendsOnly, Public = list(range(1, 4))


@unique
class CommentPrivacyState(StrEnum):
    Private, FriendsOnly, Public = [
        "commentselfonly",
        "commentfriendsonly",
        "commentanyone"
    ]
