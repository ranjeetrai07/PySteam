from steamapi import SteamID
import pytest


def test_parameterless_construction():
    sid = SteamID()
    assert sid.universe == SteamID.Universe.INVALID
    assert sid.type == SteamID.Type.INVALID
    assert sid.instance == SteamID.Instance.ALL
    assert sid.accountid == 0


def test_steam2id_construction_universe_0():
    sid = SteamID('STEAM_0:0:23071901')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_steam2id_construction_universe_1():
    sid = SteamID('STEAM_1:1:23071901')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143803


def test_steam3id_construction_individual():
    sid = SteamID('[U:1:46143802]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_steam3id_construction_gameserver():
    sid = SteamID('[G:1:31]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.GAMESERVER
    assert sid.instance == SteamID.Instance.ALL
    assert sid.accountid == 31


def test_steam3id_construction_anon_gameserver():
    sid = SteamID('[A:1:46124:11245]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.ANON_GAMESERVER
    assert sid.instance == 11245
    assert sid.accountid == 46124


def test_steam3id_construction_lobby():
    sid = SteamID('[L:1:12345]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.CHAT
    assert sid.instance == SteamID.ChatInstanceFlags.LOBBY
    assert sid.accountid == 12345


def test_steam3id_construction_lobby_with_instanceid():
    sid = SteamID('[L:1:12345:55]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.CHAT
    assert sid.instance == SteamID.ChatInstanceFlags.LOBBY | 55
    assert sid.accountid == 12345


def test_steamid64_construction_individual():
    sid = SteamID('76561198006409530')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_steamid64_construction_clan():
    sid = SteamID('103582791434202956')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.CLAN
    assert sid.instance == SteamID.Instance.ALL
    assert sid.accountid == 4681548


def test_steamid32_construction_individual():
    sid = SteamID.from_account_id('46143802')
    print(sid.__dict__)
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_invalid_construction():
    with pytest.raises(Exception):
        SteamID('invalid input')


def test_steam2id_rendering_universe_0():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.as_steam2_zero == "STEAM_0:0:23071901"
    assert sid._as_steam2(False) == "STEAM_0:0:23071901"


def test_steam2id_rendering_universe_1():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.steam_id == "STEAM_1:0:23071901"
    assert sid.as_steam2 == "STEAM_1:0:23071901"
    assert sid._as_steam2(True) == "STEAM_1:0:23071901"


def test_steam2id_rendering_non_individual():
    with pytest.raises(Exception):
        sid = SteamID()
        sid.universe = SteamID.Universe.PUBLIC
        sid.type = SteamID.Type.CLAN
        sid.instance = SteamID.Instance.DESKTOP
        sid.accountid = 4681548
        sid._as_steam2()


def test_steam3id_rendering_individual():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.as_steam3 == "[U:1:46143802]"
    assert sid.steam_id3 == "[U:1:46143802]"


def test_steam3id_rendering_anon_gameserver():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.ANON_GAMESERVER
    sid.instance = 41511
    sid.accountid = 43253156
    assert sid.as_steam3 == "[A:1:43253156:41511]"
    assert sid.steam_id3 == "[A:1:43253156:41511]"


def test_steam3id_rendering_lobby():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.CHAT
    sid.instance = SteamID.ChatInstanceFlags.LOBBY
    sid.accountid = 451932
    assert sid.as_steam3 == "[L:1:451932]"
    assert sid.steam_id3 == "[L:1:451932]"


def test_steamid64_rendering_individual():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.as_64 == 76561198006409530


def test_steamid64_rendering_individual_str():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert str(sid) == "76561198006409530"


def test_steamid64_anon_gameserver():
    sid = SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.ANON_GAMESERVER
    sid.instance = 188991
    sid.accountid = 42135013
    assert sid.as_64 == 90883702753783269


def test_invalid_new_id():
    sid = SteamID()
    assert sid.is_valid() is False


def test_invalid_individual_instance():
    sid = SteamID('[U:1:46143802:10]')
    assert sid.is_valid() is False


def test_invalid_non_all_clan_instance():
    sid = SteamID('[g:1:4681548:2]')
    assert sid.is_valid() is False


def test_invalid_gameserver_id_with_accountid_0():
    sid = SteamID('[G:1:0]')
    assert sid.is_valid() is False
