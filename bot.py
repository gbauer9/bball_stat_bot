from pandas import DataFrame
import praw, yaml, logging, sys, argparse
from typing import List
from basketball_reference_scraper.players import get_stats

# TODO: Add comparison feature
# TODO: Add advanced stat lookup
# TODO: Retry if server error
# TODO: Don't fail on no results

class PlayerNotFound(Exception):
    pass

def dfToRedditTable(df: DataFrame):
    num_cols = len(df.columns)
    header_sep = ['-'] * num_cols
    df.loc[0] = header_sep
    return df.to_csv(index=False, sep='|', line_terminator='\n')

def getStatsWrapper(name: str):
    player_stats = get_stats(name)
    if len(player_stats.index) == 0:
        raise PlayerNotFound(f"No player found with given name: {name}")
    return player_stats

def getResponse(name: str, second_name: str, stats: List[str], playoffs: bool):
    response = []

    try:
        player_stats = getStatsWrapper(name)
    except PlayerNotFound:
        raise

    response.append(player_stats)

    if second_name:
        try:
            compare_stats = getStatsWrapper(second_name)        
        except PlayerNotFound:
            raise
        
        response.append(compare_stats)

    
    return [dfToRedditTable(player_df[stats]) for player_df in response]

def makeReply(stats: List[str], comment: praw.models.Comment):
    body = '\n'.join(stats)
    comment.reply(body=body) 


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
    parser.add_argument("-c", "--compare", type=str, nargs='+', default="")
    parser.add_argument("-s", "--stats", type=str, nargs='?', default="AGE,TEAM,LEAGUE,POS,G,GS,MP,FG,FGA,FG%,3P,3PA,3P%,2P,2PA,2P%,FT,FTA,FT%,ORB,DRB")
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
                player_name = ' '.join(parsed_args.name)
                compare_name = ' '.join(parsed_args.compare)
                sel_stats = ["SEASON"] + parsed_args.stats.upper().split(',')
                
                # Try to search for given player using basketball_reference_scraper
                try:
                    response = getResponse(player_name, compare_name, sel_stats, parsed_args.playoffs)
                except Exception as err:
                    logger.warn(f"Unable to generate response: {err}")
                    response = "Unable to find results for given input."
                    
                # Reply to comment and mark as read so it's not processed again
                try:
                    makeReply(response, mention)
                except Exception as err:
                    logger.warn(f"Error occurred while replying to comment: {err}")
                mention.mark_read()