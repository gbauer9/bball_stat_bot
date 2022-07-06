import praw, yaml, logging, sys
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

@dataclass
class Request:
    full_name: str = ""
    stat_arg_idx: int = None
    ind_stats: List[str] = field(default_factory=list)

def dfToRedditTable(df):
    num_cols = len(df.columns)
    header_sep = ['-'] * num_cols
    df.loc[0] = header_sep
    return df.to_csv(index=False, sep='|', line_terminator='\n') 

def getResponse(req: Request):
    raw_stats = get_stats(req.full_name)
    if req.ind_stats:
        raw_stats = raw_stats[req.ind_stats]
    return dfToRedditTable(raw_stats)

def makeReply(stats, comment):
    header = "Results\n\n"
    comment.reply(body=header+stats) 


if __name__ == "__main__":
    # Set up logger
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
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
            print(e)

    # Get reddit instance
    reddit = praw.Reddit(
    client_id = secrets["client_id"],
    client_secret = secrets["client_secret"],
    user_agent = secrets["user_agent"],
    username = "bball_stat_bot",
    password = secrets["password"]
    )
            
    # Main loop
    while True:

        # Loop through mentions, if unread then parse, reply, and mark as read
        for mention in reddit.inbox.mentions():
            if mention.new:
                req = Request()
                args = mention.body.split(" ")

                # If request specifies specific stats, set the index of stat arg so we know where to split
                if "-s" in args:
                    req.stat_arg_idx = args.index("-s")
                    req.full_name = ' '.join(args[1:req.stat_arg_idx])
                    # BUG: eFG% is not fully capitalized, so defaulting to upper() doesn't work
                    req.ind_stats = ["SEASON"] + args[req.stat_arg_idx + 1].upper().split(",")
                else:
                    req.full_name = ' '.join(args[1:])

                formatted_stats = getResponse(req)
                makeReply(formatted_stats, mention)
                mention.mark_read()