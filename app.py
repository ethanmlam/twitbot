import feedparser
import re
import os
import tweepy
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Twitter Auth
auth = tweepy.OAuth1UserHandler(
    os.getenv("TWITTER_API_KEY"),
    os.getenv("TWITTER_API_SECRET"),
    os.getenv("TWITTER_ACCESS_TOKEN"),
    os.getenv("TWITTER_ACCESS_SECRET")
)
api = tweepy.API(auth)

# Anthropic Auth
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 1. Fetch tweet URLs from RSS
def fetch_tweet_entries(rss_url):
    feed = feedparser.parse(rss_url)
    entries = []
    for entry in feed.entries:
        match = re.search(r"status/(\d+)", entry.link)
        if match:
            entries.append({
                "id": match.group(1),
                "title": entry.title,
                "content": entry.summary
            })
    return entries

# 2. Use Anthropic to generate a tweet reply
def generate_reply(tweet_text):
    prompt = f"Reply to this build in public tweet in an insightful sentence: '{tweet_text}'"
    try:
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=60,
            temperature=1,
            system="You're a helpful, witty startup founder who builds in public. Respond with short, insightful replies to other founders.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Anthropic error: {e}")
        return None

# 3. Post reply
def reply_to_tweet(tweet_id, message):
    try:
        api.update_status(
            status=message,
            in_reply_to_status_id=tweet_id,
            auto_populate_reply_metadata=True
        )
        print(f"✅ Replied to tweet {tweet_id}: {message}")
    except Exception as e:
        print(f"❌ Error replying to {tweet_id}: {e}")

# Main
if __name__ == "__main__":
    RSS_URL = "https://rsshub.app/twitter/keyword/buildinpublic"
    entries = fetch_tweet_entries(RSS_URL)

    for entry in entries:
        reply = generate_reply(entry["title"] + " " + entry["content"])
        if reply:
            reply_to_tweet(entry["id"], reply)
