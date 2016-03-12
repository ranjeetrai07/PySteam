import re
import math


class Universe:
    INVALID = 0
    PUBLIC = 1
    BETA = 2
    INTERNAL = 3
    DEV = 4


class Type:
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


class Instance:
    ALL = 0
    DESKTOP = 1
    CONSOLE = 2
    WEB = 4


class SteamID:
    Type = Type
    Universe = Universe
    Instance = Instance

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

    AccountIDMask = 0xFFFFFFFF
    AccountInstanceMask = 0x000FFFFF

    ChatInstanceFlags = {
        "Clan": (AccountInstanceMask + 1) >> 1,
        "Lobby": (AccountInstanceMask + 1) >> 2,
        "MMSLobby": (AccountInstanceMask + 1) >> 3
    }

    def __init__(self, inp=None):
        self.universe = self.Universe.INVALID
        self.type = self.Type.INVALID
        self.instance = self.Instance.ALL
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
            self.universe = int(matches[1]) or self.Universe.PUBLIC
            self.type = self.Type.INDIVIDUAL
            self.instance = self.Instance.DESKTOP
            self.accountid = (int(matches[2]) * 2) + int(matches[1])
        elif steam3_regex.match(inp):
            matches = steam3_regex.findall(inp)[0]
            self.universe = int(matches[1])
            self.accountid = int(matches[2])

            typeChar = matches[0]
            if 0 <= 3 < len(matches):
                self.instance = int(matches[3][1:] or 0)
            elif typeChar == 'U':
                self.instance = self.Instance.DESKTOP

            if typeChar == 'c':
                self.instance |= self.ChatInstanceFlags['Clan']
                self.type = self.Type.CHAT
            elif typeChar == 'L':
                self.instance |= self.ChatInstanceFlags['Lobby']
                self.type = self.Type.CHAT
            else:
                self.type = self._getTypeFromChar(typeChar)
        elif not inp.isdigit():
            raise Exception("Not a valid steam format")
        else:
            inp = int(inp)
            self.accountid = inp & 0xFFFFFFFF
            self.instance = (inp >> 32) & 0xFFFFF
            self.type = (inp >> 52) & 0xF
            self.universe = (inp >> 56)

    def isValid():
        if self.type <= self.Type.INVALID or self.type > self.Type.ANON_USER:
            return False

        if self.universe <= self.Universe.INVALID or self.universe > self.Universe.DEV:
            return False

        if self.type == self.Type.INDIVIDUAL and ((self.accountid == 0) or self.instance > self.Instance.WEB):
            return False

        if self.type == self.Type.CLAN and ((self.accountid == 0) or self.instance != self.Instance.ALL):
            return False

        if self.type == self.Type.GAMESERVER and self.accountid == 0:
            return False

        return True

    def Steam2RenderedID(self, newerFormat=None):
        if self.type != self.Type.INDIVIDUAL:
            raise Exception(
                "Can't get Steam2 rendered ID for non-individual ID")
        else:
            universe = self.universe
            if not newerFormat and universe == 1:
                universe = 0

            return "STEAM_{x}:{y}:{z}".format(x=universe, y=(self.accountid & 1), z=int(math.floor(self.accountid / 2)))

    @property
    def Steam3RenderedID(self):
        typeChar = self.TypeChars.get(self.type, 'i')

        if self.instance & self.ChatInstanceFlags['Clan']:
            typeChar = 'c'
        elif self.instance & self.ChatInstanceFlags['Lobby']:
            typeChar = 'L'

        renderInstance = ((self.type == self.Type.ANON_GAMESERVER) or (self.type == self.Type.MULTISEAT) or (
            self.type == self.Type.INDIVIDUAL and self.instance != self.Instance.DESKTOP))

        return "[{typechar}:{universe}:{accid}{instance}]".format(
            typechar=typeChar,
            universe=self.universe,
            accid=self.accountid,
            instance=(':' + self.instance if renderInstance else ''))

    @property
    def SteamID64(self):
        return ((self.universe << 56) | (self.type << 52) | (self.instance << 32) | self.accountid)

    def __str__(self):
        return str(self.SteamID64)

    def __repr__(self):
        return "SteamID.SteamID('{}')".format(self.SteamID64)

    def _getTypeFromChar(self, typeChar):
        for type_ in self.TypeChars:
            if self.TypeChars[type_] == typeChar:
                return int(type_)

        return self.Type.INVALID
