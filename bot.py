import praw, yaml 
from basketball_reference_scraper.players import get_stats

# TODO: Type hints
# TODO: Convert Request to dataclass
# TODO: Better input parsing
# TODO: Add comparison feature


class Request:
    def __init__(self, full_name = None, stat_arg_idx = None, ind_stats = []):
        self.full_name = full_name
        self.stat_arg_idx = stat_arg_idx
        self.ind_stats = ind_stats

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
    # Get secrets needed to connect to Reddit from secrets file
    with open("secrets.yaml") as stream:
        try:
            secrets = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print(e)
    
    # Main loop
    while True:

        # Get reddit instance
        reddit = praw.Reddit(
        client_id = secrets["client_id"],
        client_secret = secrets["client_secret"],
        user_agent = secrets["user_agent"],
        username = "bball_stat_bot",
        password = secrets["password"]
        )

        # Loop through mentions, if unread then parse, reply, and mark as read
        for mention in reddit.inbox.mentions():
            if mention.new:
                req = Request()
                args = mention.body.split(" ")

                # If request specifies specific stats, set the index of stat arg so we know where to split
                if "stats" in args:
                    req.stat_arg_idx = args.index("stats")
                    req.full_name = ' '.join(args[1:req.stat_arg_idx])
                    req.ind_stats = ["SEASON"] + args[req.stat_arg_idx + 1].upper().split(",")
                else:
                    req.full_name = ' '.join(args[1:])

                formatted_stats = getResponse(req)
                makeReply(formatted_stats, mention)
                mention.mark_read()