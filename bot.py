from pandas import DataFrame
import praw, yaml, logging, sys, argparse
from dataclasses import dataclass, field
from typing import List
from basketball_reference_scraper.players import get_stats

# TODO: Type hints
# TODO: Better input parsing/don't fail on bad input
# TODO: Add comparison feature
# TODO: Retry if server error

POSSIBLE_STATS = {
    "G",
    "GS",
    "MP",
    "FG",
    "FGA",
    "FG%",
    "3P",
    "3PA",
    "3P%",
    "2P",
    "2PA",
    "2P%",
    "eFG%",
    "FT",
    "FTA",
    "FT%",
    "ORB",
    "DRB"
}

def dfToRedditTable(df: DataFrame):
    num_cols = len(df.columns)
    header_sep = ['-'] * num_cols
    df.loc[0] = header_sep
    return df.to_csv(index=False, sep='|', line_terminator='\n') 

def getResponse(name: str, stats: List[str]):
    return dfToRedditTable(get_stats(name)[stats])

def makeReply(stats, comment):
    header = "Results\n\n"
    comment.reply(body=header+stats) 


if __name__ == "__main__":
    # Set up logger
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)s] [%(levelname)s]  %(message)s")
    rootLogger = logging.getLogger()

    fileHandler = logging.FileHandler("bball_stat_bot.log", mode='w')
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)
    rootLogger.setLevel(logging.INFO)

    # Get secrets needed to connect to Reddit from secrets file
    with open("secrets.yaml") as stream:
        try:
            secrets = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            rootLogger.critical("Unable to parse secrets.yaml", exc_info=True)
            exit(1)

    # Get reddit instance
    reddit = praw.Reddit(
    client_id = secrets["client_id"],
    client_secret = secrets["client_secret"],
    user_agent = secrets["user_agent"],
    username = "bball_stat_bot",
    password = secrets["password"]
    )

    # Set up arg parser
    parser = argparse.ArgumentParser()
    parser.add_argument("name", type=str, nargs='+')
    parser.add_argument("-s", "--stats", nargs='?', default="AGE,TEAM,LEAGUE,POS,G,GS,MP,FG,FGA,FG%,3P,3PA,3P%,2P,2PA,2P%,FT,FTA,FT%,ORB,DRB,TRB,STL,BLK,TOV,PF,PTS")
            
    # Main loop
    while True:

        # Loop through mentions, if unread then parse, reply, and mark as read
        for mention in reddit.inbox.mentions():
            if mention.new:
                rootLogger.info(f"Processing request: {mention.body}")
                args = mention.body.split(" ")[1:]

                # If request specifies specific stats, set the index of stat arg so we know where to split
                parsed_args = parser.parse_args(args)
                player_name = ' '.join(parsed_args.name)
                sel_stats = ["SEASON"] + parsed_args.stats.upper().split(',')
                
                formatted_stats = getResponse(player_name, sel_stats)
                makeReply(formatted_stats, mention)
                mention.mark_read()