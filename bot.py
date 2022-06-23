import praw, yaml 
from basketball_reference_scraper.players import get_stats

def dfToRedditTable(df):
    num_cols = len(df.columns)
    header_sep = ['-'] * num_cols
    df.loc[0] = header_sep
    return df.to_csv(index=False, sep='|', line_terminator='\n') 

def makeReply(player_name, stats, comment):
    header = f"Results for {player_name}:\n\n"
    comment.reply(body=header+stats) 


if __name__ == "__main__":
    with open("secrets.yaml") as stream:
        try:
            secrets = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print(e)
    while True:
        reddit = praw.Reddit(
        client_id = secrets["client_id"],
        client_secret = secrets["client_secret"],
        user_agent = secrets["user_agent"],
        username = "bball_stat_bot",
        password = secrets["password"]
        )

        for mention in reddit.inbox.mentions():
            if mention.new:
                args = mention.body.split(' ')
                full_name = ' '.join(args[1:])
                stats = get_stats(full_name)
                formatted_stats = dfToRedditTable(stats)
                makeReply(full_name, formatted_stats, mention)
                mention.mark_read()