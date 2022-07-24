import praw, yaml, logging, sys, argparse
from dataclasses import dataclass
from pandas import DataFrame, concat
from typing import List, Tuple
from basketball_reference_scraper.players import get_stats
from datetime import date

# TODO: UPDATE ALL TESTS
# TODO: Put on AWS
# TODO: Rename variables to make more sense
# TODO: Create CI/CD pipeline
# TODO: Move all arg parsing into separate function


class PlayerNotFound(Exception):
    pass


class YearNotFound(Exception):
    pass


@dataclass
class PlayerResponse:
    name: str
    stats: str


def dfToRedditTable(df: DataFrame):
    # Reddit tables need a row of "-" to separate headers from data
    num_cols = len(df.columns)
    header_sep = DataFrame([["-"] * num_cols], columns=df.columns)

    # Insert header seperator row at top of stats dataframe
    df = concat([header_sep, df], ignore_index=True)

    return df.to_csv(index=False, sep="|", line_terminator="\n")


def getStatsWrapper(name: str, playoffs: bool, advanced: bool, year: int):
    player_stats = get_stats(
        name, playoffs=playoffs, stat_type="ADVANCED" if advanced else "PER_GAME"
    )
    if len(player_stats.index) == 0:
        raise PlayerNotFound(f"No player found with given name: {name}")

    if year:
        season = f"{year-1}-{str(year)[-2:]}"
        player_stats = player_stats.loc[player_stats["SEASON"] == season]

    if len(player_stats.index) == 0:
        raise YearNotFound(f"Player {name} did not play in season {season}")
    return player_stats


def isValidInput(player_one: str, player_two: str, year: int):
    if not player_one:
        return False

    if player_one.lower() == player_two.lower():
        return False

    if year:
        if not (1947 <= year <= date.today().year):
            return False

    return True


def getResponse(name: str, second_name: str, playoffs: bool, year: int, advanced: bool):
    response: List[Tuple(str, DataFrame)] = []

    # Try to get data of first player, append (name, df) to response
    try:
        player_stats = getStatsWrapper(name, playoffs, advanced, year)
    except Exception:
        raise

    response.append((name, player_stats))

    # Try to get data of second player, append (name, df)
    if second_name:
        try:
            compare_stats = getStatsWrapper(second_name, playoffs, advanced, year)
        except Exception:
            raise

        response.append((second_name, compare_stats))

    # Return a list of PlayerResponse object which have the player name and redditified stats
    return [
        PlayerResponse(player[0], dfToRedditTable(player[1])) for player in response
    ]


def makeReply(stats: List[PlayerResponse], comment: praw.models.Comment):
    body = ""
    for player in stats:
        body += f"Stats for {player.name}:\n\n"
        body += f"{player.stats}\n\n"
    comment.reply(body=body)


if __name__ == "__main__":
    # Set up logger
    logFormatter = logging.Formatter(
        "%(asctime)s [%(threadName)s] [%(levelname)s]  %(message)s"
    )
    logger = logging.getLogger()

    fileHandler = logging.FileHandler("bball_stat_bot.log", mode="w")
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    logger.setLevel(logging.INFO)

    # Get secrets needed to connect to Reddit from secrets file
    with open("secrets.yaml") as stream:
        try:
            secrets = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            logger.critical("Unable to parse secrets.yaml", exc_info=True)
            exit(1)

    # Get reddit instance
    reddit = praw.Reddit(
        client_id=secrets["client_id"],
        client_secret=secrets["client_secret"],
        user_agent=secrets["user_agent"],
        username="bball_stat_bot",
        password=secrets["password"],
    )

    # Set up arg parser
    parser = argparse.ArgumentParser()
    parser.add_argument("name", type=str, nargs="+")
    parser.add_argument("-c", "--compare", type=str, nargs="+", default="")
    parser.add_argument("-y", "--year", type=int, nargs="?", const=2022, default=None)
    parser.add_argument("-p", "--playoffs", action="store_true")
    parser.add_argument("-a", "--advanced", action="store_true")

    # Main loop
    while True:

        # Loop through mentions, if unread then parse, reply, and mark as read
        for mention in reddit.inbox.mentions():
            if mention.new:
                logger.info(f"Processing request: {mention.body}")
                args = mention.body.split(" ")[1:]

                # Parse args and get player names
                parsed_args = parser.parse_args(args)
                player_name = " ".join(parsed_args.name)
                compare_name = " ".join(parsed_args.compare)

                # Check input for validity, if not then reply
                if not isValidInput(player_name, compare_name, parsed_args.year):
                    mention.reply(body="Invalid input.")
                    mention.mark_read()
                    continue

                # Try to search for given player using basketball_reference_scraper
                try:
                    response = getResponse(
                        player_name,
                        compare_name,
                        parsed_args.playoffs,
                        parsed_args.year,
                        parsed_args.advanced,
                    )
                except Exception as err:
                    logger.warn(f"Unable to generate response: {err}", exc_info=True)
                    mention.reply(
                        body="Unable to find results for one of or both players."
                    )
                    mention.mark_read()
                    continue

                # Reply to comment and mark as read so it's not processed again
                try:
                    makeReply(response, mention)
                except Exception as err:
                    logger.warn(
                        f"Error occurred while replying to comment: {err}",
                        exc_info=True,
                    )
                mention.mark_read()
