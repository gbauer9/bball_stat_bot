import src.bball_stat_bot as stat_bot, pandas as pd, pytest


class TestDfToRedditTable:
    def testOne(self):
        self.df = pd.DataFrame(
            {
                "SEASON": ["2020-2021"],
                "AGE": ["25.0"],
                "TEAM": ["POR"],
                "LEAGUE": ["NBA"],
            }
        )
        print(self.df)

        self.transformed = stat_bot.dfToRedditTable(self.df)

        print(self.transformed)
        assert (
            self.transformed
            == "SEASON|AGE|TEAM|LEAGUE\n-|-|-|-\n2020-2021|25.0|POR|NBA\n"
        )

    def testTwo(self):
        self.df = pd.DataFrame(
            {
                "SEASON": ["2018-2019", "2019-2020"],
                "AGE": [25.0, 26.0],
                "TEAM": ["POR", "LAL"],
                "LEAGUE": ["NBA", "ABA"],
            }
        )
        print(self.df)

        self.transformed = stat_bot.dfToRedditTable(self.df)

        print(self.transformed)
        assert (
            self.transformed
            == "SEASON|AGE|TEAM|LEAGUE\n-|-|-|-\n2018-2019|25.0|POR|NBA\n2019-2020|26.0|LAL|ABA\n"
        )


def testPlayerNotFoundException(monkeypatch):
    def mockGetStats(name: str, playoffs: bool):
        return pd.DataFrame([])

    monkeypatch.setattr(
        "src.bball_stat_bot.get_stats", mockGetStats
    )

    with pytest.raises(stat_bot.PlayerNotFound):
        _ = stat_bot.getStatsWrapper("test", False)

def testHappyPath(monkeypatch):
    def mockGetStats(name: str, playoffs: bool):
        return pd.DataFrame(
            {
                "SEASON": ["2020-2021", "2021-2022"],
                "AGE": [23.0, 24.0],
                "TEAM": ["TOR", "TOR"],
                "LEAGUE": ["NBA", "NBA"],
            }
        )

    monkeypatch.setattr(
        "src.bball_stat_bot.get_stats", mockGetStats
    )
    
    assert stat_bot.getStatsWrapper("test", False).equals(pd.DataFrame(
        {
            "SEASON": ["2020-2021", "2021-2022"],
            "AGE": [23.0, 24.0],
            "TEAM": ["TOR", "TOR"],
            "LEAGUE": ["NBA", "NBA"],
        }
    ))
