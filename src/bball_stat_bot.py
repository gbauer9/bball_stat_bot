from dataclasses import dataclass
from pandas import DataFrame, concat
import praw, yaml, logging, sys, argparse
from requests import head
from typing import List, Tuple
from basketball_reference_scraper.players import get_stats

# TODO: Write unit tests so I don't have to keep making new reddit comments
# TODO: Put on AWS
# TODO: Rename variables to make more sense
# TODO: Create CI/CD pipeline
# TODO: Add advanced stat lookup
# TODO: Retry if server error
# TODO: Possibly limit # of years so as to not clutter


class PlayerNotFound(Exception):
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


def getStatsWrapper(name: str, playoffs: bool):
    player_stats = get_stats(name, playoffs=playoffs)
    if len(player_stats.index) == 0:
        raise PlayerNotFound(f"No player found with given name: {name}")
    return player_stats


def getResponse(name: str, second_name: str, stats: List[str], playoffs: bool):
    response: List[Tuple(str, DataFrame)] = []

    # Try to get data of first player, append (name, df) to response
    try:
        player_stats = getStatsWrapper(name, playoffs)
    except Exception:
        raise

    response.append((name, player_stats[stats]))

    # Try to get data of second player, append (name, df)
    if second_name:
        try:
            compare_stats = getStatsWrapper(second_name, playoffs)
        except Exception:
            raise

        response.append((second_name, compare_stats[stats]))

    # Return a list of PlayerResponse object which have the player name and redditified stats
    return [
        PlayerResponse(player[0], dfToRedditTable(player[1][stats]))
        for player in response
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
    parser.add_argument(
        "-s",
        "--stats",
        type=str,
        nargs="?",
        default="AGE,TEAM,LEAGUE,POS,G,GS,MP,FG,FGA,FG%,3P,3PA,3P%,2P,2PA,2P%,FT,FTA,FT%,ORB,DRB,TRB,AST,STL,BLK,TOV,PF,PTS",
    )
    parser.add_argument("-p", "--playoffs", action="store_true")

    # Main loop
    while True:

        # Loop through mentions, if unread then parse, reply, and mark as read
        for mention in reddit.inbox.mentions():
            if mention.new:
                logger.info(f"Processing request: {mention.body}")
                args = mention.body.split(" ")[1:]

                # Parse args and get player names/stats
                parsed_args = parser.parse_args(args)
                player_name = " ".join(parsed_args.name)
                compare_name = " ".join(parsed_args.compare)
                sel_stats = ["SEASON"] + parsed_args.stats.upper().split(",")

                # Try to search for given player using basketball_reference_scraper
                try:
                    response = getResponse(
                        player_name, compare_name, sel_stats, parsed_args.playoffs
                    )
                except Exception as err:
                    logger.warn(f"Unable to generate response: {err}")
                    mention.reply(body="Unable to find results one/both players.")
                    mention.mark_read()
                    continue

                # Reply to comment and mark as read so it's not processed again
                try:
                    makeReply(response, mention)
                except Exception as err:
                    logger.warn(f"Error occurred while replying to comment: {err}")
                mention.mark_read()
