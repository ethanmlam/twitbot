import feedparser
import re
import os
import tweepy
import openai
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

# OpenAI Auth
openai.api_key = os.getenv("OPENAI_API_KEY")

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

# 2. Use OpenAI to generate a tweet reply
def generate_reply(tweet_text):
    prompt = f"You're a helpful, witty startup founder. Reply to this build in public tweet: '{tweet_text}'"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_tokens=60
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
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
