import re
import math
from enum import IntEnum, unique


@unique
class Universe(IntEnum):
    INVALID = 0
    PUBLIC = 1
    BETA = 2
    INTERNAL = 3
    DEV = 4


@unique
class Type(IntEnum):
    INVALID = 0
    INDIVIDUAL = 1
    MULTISEAT = 2
    GAMESERVER = 3
    ANON_GAMESERVER = 4
    PENDING = 5
    CONTENT_SERVER = 6
    CLAN = 7
    CHAT = 8
    P2P_SUPER_SEEDER = 9
    ANON_USER = 10


@unique
class Instance(IntEnum):
    ALL = 0
    DESKTOP = 1
    CONSOLE = 2
    WEB = 4


AccountIDMask = 0xFFFFFFFF
AccountInstanceMask = 0x000FFFFF


@unique
class ChatInstanceFlags(IntEnum):
    CLAN = (AccountInstanceMask + 1) >> 1
    LOBBY = (AccountInstanceMask + 1) >> 2
    MMSLOBBY = (AccountInstanceMask + 1) >> 3


class SteamID(object):
    Type = Type
    Universe = Universe
    Instance = Instance
    ChatInstanceFlags = ChatInstanceFlags

    TypeChars = {}
    TypeChars[Type.INVALID] = 'I'
    TypeChars[Type.INDIVIDUAL] = 'U'
    TypeChars[Type.MULTISEAT] = 'M'
    TypeChars[Type.GAMESERVER] = 'G'
    TypeChars[Type.ANON_GAMESERVER] = 'A'
    TypeChars[Type.PENDING] = 'P'
    TypeChars[Type.CONTENT_SERVER] = 'C'
    TypeChars[Type.CLAN] = 'g'
    TypeChars[Type.CHAT] = 'T'
    TypeChars[Type.ANON_USER] = 'a'

    def __init__(self, inp=None):
        """Represents a Steam ID.

        Parameters
        ----------
        inp : int or str, optional
            Initial input to base Steam ID from.

        Raises
        ------
        Exception
            Raised if not a valid steam format.
        """
        self.universe = Universe.INVALID
        self.type = Type.INVALID
        self.instance = Instance.ALL
        self.accountid = 0

        if inp is None:
            return

        inp = str(inp)
        steam2_regex = re.compile(r"^STEAM_([0-5]):([0-1]):([0-9]+)$")
        steam3_regex = re.compile(
            r"^\[([a-zA-Z]):([0-5]):([0-9]+)(:[0-9]+)?\]$")
        if steam2_regex.match(inp):
            # Steam2 ID
            matches = steam2_regex.findall(inp)[0]
            self.universe = Universe(int(matches[1])) or Universe.PUBLIC
            self.type = Type.INDIVIDUAL
            self.instance = Instance.DESKTOP
            self.accountid = (int(matches[2]) * 2) + int(matches[1])
        elif steam3_regex.match(inp):
            matches = steam3_regex.findall(inp)[0]
            self.universe = Universe(int(matches[1]))
            self.accountid = int(matches[2])

            typeChar = matches[0]
            if 0 <= 3 < len(matches) and matches[3]:
                self.instance = int(matches[3][1:] or 0)
                if self.instance in Instance:
                    self.instance = Instance(self.instance)
            elif typeChar == 'U':
                self.instance = Instance.DESKTOP

            if typeChar == 'c':
                self.instance |= ChatInstanceFlags.CLAN
                self.type = Type.CHAT
            elif typeChar == 'L':
                self.instance |= ChatInstanceFlags.LOBBY
                self.type = Type.CHAT
            else:
                self.type = Type(self._getTypeFromChar(typeChar))
        elif not inp.isdigit():
            raise Exception("Not a valid steam format")
        else:
            inp = int(inp)
            self.accountid = int(inp & 0xFFFFFFFF)
            self.instance = Instance((inp >> 32) & 0xFFFFF)
            self.type = Type((inp >> 52) & 0xF)
            self.universe = Universe(inp >> 56)

    @staticmethod
    def from_account_id(accountid):
        """Creates a ``steamapi.SteamID`` instance from an account ID (aka Steam32 ID).

        Parameters
        ----------
        accountid : int or str
            The account ID to create a ``steamapi.SteamID`` instance from.

        Returns
        -------
        ``steamapi.SteamID``
            Instance of ``steamapi.SteamID`` with `accountid`.
        """
        sid = SteamID()
        sid.universe = SteamID.Universe.PUBLIC
        sid.type = SteamID.Type.INDIVIDUAL
        sid.instance = SteamID.Instance.DESKTOP
        sid.accountid = int(accountid) if isinstance(
            accountid, int) or accountid.isdigit() else 0
        return sid

    def is_valid(self):
        """Checks if current steam ID is valid.

        Returns
        -------
        bool
            True if valid, otherwise False.
        """
        if self.type <= Type.INVALID or self.type > Type.ANON_USER:
            return False

        if self.universe <= Universe.INVALID or self.universe > Universe.DEV:
            return False

        if self.type == Type.INDIVIDUAL and ((self.accountid == 0) or self.instance > Instance.WEB):
            return False

        if self.type == Type.CLAN and ((self.accountid == 0) or self.instance != Instance.ALL):
            return False

        if self.type == Type.GAMESERVER and self.accountid == 0:
            return False

        return True

    def _as_steam2(self, newerFormat=True):
        """Outputs steam ID in Steam ID2 format (e.g ``STEAM_1:0:1234``)

        Parameters
        ----------
        newerFormat : bool, optional
            Whether to use the new public universe for IDs.
            Refer to note.

        Returns
        -------
        str
            Steam ID in Steam ID2 format (e.g ``STEAM_1:0:1234``)

        Raises
        ------
        Exception
            Raised if trying to render a non-individual ID as Steam ID2.
        """
        if self.type != Type.INDIVIDUAL:
            raise Exception(
                "Can't get Steam2 rendered ID for non-individual ID")
        else:
            universe = self.universe
            if not newerFormat and universe == 1:
                universe = 0

            return "STEAM_{x}:{y}:{z}".format(x=universe, y=(self.accountid & 1), z=int(math.floor(self.accountid / 2)))

    @property
    def as_steam2(self):
        """Outputs steam ID in Steam ID2 format (e.g ``STEAM_1:0:1234``)

        Note
        ____
        ``STEAM_X:Y:Z``. The value of ``X`` should represent the universe, or ``1``
        for ``Public``. However, there was a bug in GoldSrc and Orange Box games
        and ``X`` was ``0``. If you need that format use :attr:`SteamID.as_steam2_zero`

        Returns
        -------
        str
            Steam ID in Steam ID2 format (e.g ``STEAM_1:0:1234``)
        """
        return self._as_steam2()

    @property
    def as_steam2_zero(self):
        """For GoldSrc and Orange Box games.

        See :attr:`SteamID.as_steam2`

        Returns
        -------
        str
            Steam ID in Steam ID2 format (e.g ``STEAM_1:0:1234``)
        """
        return self._as_steam2(newerFormat=False)

    @property
    def as_steam3(self):
        """Outputs steam ID in Steam ID3 format (e.g ``[U:1:1234]``)

        Returns
        -------
        str
            Steam ID in Steam ID3 format (e.g ``[U:1:1234]``)
        """
        typeChar = self.TypeChars.get(self.type, 'i')

        if self.instance & ChatInstanceFlags.CLAN:
            typeChar = 'c'
        elif self.instance & ChatInstanceFlags.LOBBY:
            typeChar = 'L'

        renderInstance = ((self.type == Type.ANON_GAMESERVER) or (self.type == Type.MULTISEAT) or (
            self.type == Type.INDIVIDUAL and self.instance != Instance.DESKTOP))

        return "[{typechar}:{universe}:{accid}{instance}]".format(
            typechar=typeChar,
            universe=self.universe,
            accid=self.accountid,
            instance=(':' + str(self.instance) if renderInstance else ''))

    @property
    def as_32(self):
        return (self.as_64 - 76561197960265728)

    @property
    def as_64(self):
        return ((self.universe << 56) | (self.type << 52) | (self.instance << 32) | self.accountid)

    @property
    def steam_id(self):
        return self._as_steam2()

    @property
    def steam_id3(self):
        return self.as_steam3

    def __str__(self):
        return str(self.as_64)

    def __repr__(self):
        return "SteamID.SteamID('{}')".format(self.as_64)

    def _getTypeFromChar(self, typeChar):
        """Gets type based on character

        Parameters
        ----------
        typeChar : str
            Character to get relevant type from.

        Returns
        -------
        ``SteamID.Type``
            Type derived from `typeChar`.
        """
        for type_ in self.TypeChars:
            if self.TypeChars[type_] == typeChar:
                return int(type_)

        return self.Type.INVALID
