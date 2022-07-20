import src.bball_stat_bot as stat_bot, pandas as pd, pytest


def testDfToRedditTable():
    df = pd.DataFrame(
        {
            "SEASON": ["2020-2021"],
            "AGE": [25.0],
            "TEAM": ["POR"],
            "LEAGUE": ["NBA"],
        }
    )
    print(df)

    transformed = stat_bot.dfToRedditTable(df)

    print(transformed)
    assert transformed == "SEASON|AGE|TEAM|LEAGUE\n-|-|-|-\n2020-2021|25.0|POR|NBA\n"


def testGetStatsWrapperException(monkeypatch):
    def mockGetStats(name: str, playoffs: bool):
        return pd.DataFrame([])

    monkeypatch.setattr("src.bball_stat_bot.get_stats", mockGetStats)

    with pytest.raises(stat_bot.PlayerNotFound):
        _ = stat_bot.getStatsWrapper("test", False)


def testGetStatsWrapperHappyPath(monkeypatch):
    def mockGetStats(name: str, playoffs: bool):
        return pd.DataFrame(
            {
                "SEASON": ["2020-2021", "2021-2022"],
                "AGE": [23.0, 24.0],
                "TEAM": ["TOR", "TOR"],
                "LEAGUE": ["NBA", "NBA"],
            }
        )

    monkeypatch.setattr("src.bball_stat_bot.get_stats", mockGetStats)

    assert stat_bot.getStatsWrapper("test", False).equals(
        pd.DataFrame(
            {
                "SEASON": ["2020-2021", "2021-2022"],
                "AGE": [23.0, 24.0],
                "TEAM": ["TOR", "TOR"],
                "LEAGUE": ["NBA", "NBA"],
            }
        )
    )


def testGetResponseException(monkeypatch):
    def mockGetStats(name: str, playoffs: bool):
        return pd.DataFrame([])

    monkeypatch.setattr("src.bball_stat_bot.get_stats", mockGetStats)

    with pytest.raises(stat_bot.PlayerNotFound):
        _ = stat_bot.getResponse(
            "Test", "", ["SEASON", "AGE", "TEAM", "LEAGUE"], False, 2022
        )


def testGetResponseOnePlayer(monkeypatch):
    def mockGetStats(name: str, playoffs: bool):
        return pd.DataFrame(
            {
                "SEASON": ["2020-2021", "2021-2022"],
                "AGE": [23.0, 24.0],
                "TEAM": ["TOR", "TOR"],
                "LEAGUE": ["NBA", "NBA"],
            }
        )

    monkeypatch.setattr("src.bball_stat_bot.get_stats", mockGetStats)

    player_name = "Damian Lillard"

    assert stat_bot.getResponse(
        player_name, "", ["SEASON", "AGE", "TEAM", "LEAGUE"], False, 2022
    ) == [
        stat_bot.PlayerResponse(
            player_name,
            "SEASON|AGE|TEAM|LEAGUE\n-|-|-|-\n2020-2021|23.0|TOR|NBA\n2021-2022|24.0|TOR|NBA\n",
        )
    ]


def testGetResponseTwoPlayers(monkeypatch):
    def mockGetStats(name: str, playoffs: bool):
        return pd.DataFrame(
            {
                "SEASON": ["2020-2021", "2021-2022"],
                "AGE": [23.0, 24.0],
                "TEAM": ["TOR", "TOR"],
                "LEAGUE": ["NBA", "NBA"],
            }
        )

    monkeypatch.setattr("src.bball_stat_bot.get_stats", mockGetStats)

    player_one, player_two = "Jusuf Nurkic", "Keljin Blevins"

    assert stat_bot.getResponse(
        player_one, player_two, ["SEASON", "AGE", "TEAM", "LEAGUE"], False, 2022
    ) == [
        stat_bot.PlayerResponse(
            player_one,
            "SEASON|AGE|TEAM|LEAGUE\n-|-|-|-\n2020-2021|23.0|TOR|NBA\n2021-2022|24.0|TOR|NBA\n",
        ),
        stat_bot.PlayerResponse(
            player_two,
            "SEASON|AGE|TEAM|LEAGUE\n-|-|-|-\n2020-2021|23.0|TOR|NBA\n2021-2022|24.0|TOR|NBA\n",
        ),
    ]
