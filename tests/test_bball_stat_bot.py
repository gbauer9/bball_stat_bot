import src.bball_stat_bot as stat_bot, pandas as pd


class TestDfToRedditTable:
    def test_one(self):
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
        assert self.transformed == "SEASON|AGE|TEAM|LEAGUE\n-|-|-|-\n2020-2021|25.0|POR|NBA\n"