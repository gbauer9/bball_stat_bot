import praw
from basketball_reference_scraper.players import get_stats
from basketball_reference_scraper.teams import get_team_stats

def dfToRedditTable(df):
    num_cols = len(df.columns)
    header_sep = ['-'] * num_cols
    df.loc[0] = header_sep
    return df.to_csv(index=False, sep='|', line_terminator='\n') 

def makeReply(player_name, stats, comment):
    header = f"Results for {player_name}:\n\n"
    comment.reply(body=header+stats) 


if __name__ == "__main__":
    while True:
        reddit = praw.Reddit(
        client_id = "g-6aGMnmwz60b8Eq3xi2iQ",
        client_secret = "ynPerVObIr8qsefIgVUsbQyTflCQ8A",
        user_agent = "python:com.example.bball_stat_bot:v0.1 (by u/canned_food)",
        username = "bball_stat_bot",
        password = "FBu$&Srb8j$sQ.c"
        )

        for mention in reddit.inbox.mentions():
            if mention.new:
                args = mention.body.split(' ')
                
                full_name = ' '.join(args[1:])
                stats = get_stats(full_name)
                formatted_stats = dfToRedditTable(stats)
                makeReply(full_name, formatted_stats, mention)
                mention.mark_read()