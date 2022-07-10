from pandas import DataFrame
import praw, yaml, logging, sys, argparse
from typing import List
from basketball_reference_scraper.players import get_stats

# TODO: Add comparison feature
# TODO: Add advanced stat lookup
# TODO: Retry if server error
# TODO: Don't fail on no results

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

class PlayerNotFound(Exception):
    pass

def dfToRedditTable(df: DataFrame):
    num_cols = len(df.columns)
    header_sep = ['-'] * num_cols
    df.loc[0] = header_sep
    return df.to_csv(index=False, sep='|', line_terminator='\n') 

def getResponse(name: str, stats: List[str], playoffs: bool):
    player_stats = get_stats(name)
    if len(player_stats.index) == 0:
        raise PlayerNotFound("No player found with given name") 
    return dfToRedditTable(get_stats(name, playoffs=playoffs)[stats])

def makeReply(stats: str, comment: praw.models.Comment):
    comment.reply(body=stats) 


if __name__ == "__main__":
    # Set up logger
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)s] [%(levelname)s]  %(message)s")
    logger = logging.getLogger()

    fileHandler = logging.FileHandler("bball_stat_bot.log", mode='w')
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
    parser.add_argument("-p", "--playoffs", action="store_true")
            
    # Main loop
    while True:

        # Loop through mentions, if unread then parse, reply, and mark as read
        for mention in reddit.inbox.mentions():
            if mention.new:
                logger.info(f"Processing request: {mention.body}")
                args = mention.body.split(" ")[1:]

                # If request specifies specific stats, set the index of stat arg so we know where to split
                parsed_args = parser.parse_args(args)
                player_name = ' '.join(parsed_args.name)
                sel_stats = ["SEASON"] + parsed_args.stats.upper().split(',')
                
                # Try to search for given player using basketball_reference_scraper
                try:
                    response = getResponse(player_name, sel_stats, parsed_args.playoffs)
                except Exception as err:
                    logger.warn(f"Unable to generate response: {err}")
                    response = "Unable to find results for given input."
                    
                # Reply to comment and mark as read so it's not processed again
                try:
                    makeReply(response, mention)
                except Exception as err:
                    logger.warn(f"Error occurred while replying to comment: {err}")
                mention.mark_read()