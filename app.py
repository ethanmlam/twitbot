import feedparser
import re
import os
import tweepy
import anthropic
import time
import json
import asyncio
import random
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Twitter Auth - using API v2
api = tweepy.Client(
    consumer_key=os.getenv("TWITTER_API_KEY"),
    consumer_secret=os.getenv("TWITTER_API_SECRET"),
    access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
    access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
)

# Anthropic Auth
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Constants
RATE_LIMIT_FILE = "tweet_rate_limit.json"
SEEN_TWEETS_FILE = "seen_tweets.json"
POLL_STATS_FILE = "poll_stats.json"
MAX_TWEETS_PER_DAY = 16  # Rate limit for tweets per day
MAX_POLLS_PER_DAY = 50   # Rate limit for polls per day
MAX_REPLIES_PER_MONTH = 500  # Rate limit for replies per month
RSSHUB_URL = os.getenv("RSSHUB_URL")  # Use environment variable if available

# Test users
USERS = ["spydaris", "aviderring", "elonmusk",]

# Rate limiting functions
def load_rate_limit_data():
    """Load the rate limit data from file"""
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading rate limit data: {e}")
    
    # Return default data if file doesn't exist or there's an error
    return {
        "tweets": [],
        "last_reset": datetime.now().isoformat(),
        "monthly_replies": [],
        "last_monthly_reset": datetime.now().isoformat(),
        "daily_polls": [],
        "last_poll_reset": datetime.now().isoformat()
    }

def save_rate_limit_data(data):
    """Save the rate limit data to file"""
    try:
        with open(RATE_LIMIT_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving rate limit data: {e}")

def can_send_tweet():
    """Check if we can send a tweet based on daily and monthly rate limits"""
    data = load_rate_limit_data()
    
    # Convert timestamps from string to datetime
    last_reset = datetime.fromisoformat(data.get("last_reset", datetime.now().isoformat()))
    last_monthly_reset = datetime.fromisoformat(data.get("last_monthly_reset", datetime.now().isoformat()))
    now = datetime.now()
    
    # If it's been more than 24 hours since the last daily reset, reset the counter
    if now - last_reset > timedelta(hours=24):
        data["tweets"] = []
        data["last_reset"] = now.isoformat()
        save_rate_limit_data(data)
    
    # If it's been more than a month since the last monthly reset, reset the counter
    if now - last_monthly_reset > timedelta(days=30):
        data["monthly_replies"] = []
        data["last_monthly_reset"] = now.isoformat()
        save_rate_limit_data(data)
    
    # Check if we're under the daily limit
    if len(data.get("tweets", [])) >= MAX_TWEETS_PER_DAY:
        logger.warning(f"⚠️ Daily rate limit reached: {len(data['tweets'])}/{MAX_TWEETS_PER_DAY} tweets in the last 24 hours")
        return False
    
    # Check if we're under the monthly limit
    if len(data.get("monthly_replies", [])) >= MAX_REPLIES_PER_MONTH:
        logger.warning(f"⚠️ Monthly rate limit reached: {len(data['monthly_replies'])}/{MAX_REPLIES_PER_MONTH} replies in the last month")
        return False
    
    return True

def can_poll_feed():
    """Check if we can poll a feed based on daily rate limits"""
    data = load_rate_limit_data()
    
    # Convert timestamps from string to datetime
    last_poll_reset = datetime.fromisoformat(data.get("last_poll_reset", datetime.now().isoformat()))
    now = datetime.now()
    
    # If it's been more than 24 hours since the last poll reset, reset the counter
    if now - last_poll_reset > timedelta(hours=24):
        data["daily_polls"] = []
        data["last_poll_reset"] = now.isoformat()
        save_rate_limit_data(data)
    
    # Check if we're under the daily poll limit
    if len(data.get("daily_polls", [])) >= MAX_POLLS_PER_DAY:
        logger.warning(f"⚠️ Daily poll limit reached: {len(data['daily_polls'])}/{MAX_POLLS_PER_DAY} polls in the last 24 hours")
        return False
    
    return True

def track_poll():
    """Track that we polled a feed"""
    data = load_rate_limit_data()
    
    # Add the new poll with timestamp
    data.setdefault("daily_polls", []).append({
        "timestamp": datetime.now().isoformat()
    })
    
    # Save the updated data
    save_rate_limit_data(data)
    
    # Log the current rate limit status
    polls_used = len(data.get("daily_polls", []))
    remaining = MAX_POLLS_PER_DAY - polls_used
    logger.info(f"📊 Poll rate limit status: {polls_used}/{MAX_POLLS_PER_DAY} polls used (remaining: {remaining})")

def track_sent_tweet(tweet_id):
    """Track that we sent a tweet"""
    data = load_rate_limit_data()
    
    # Add the new tweet with timestamp
    data.setdefault("tweets", []).append({
        "id": tweet_id,
        "timestamp": datetime.now().isoformat()
    })
    
    # Add to monthly replies as well
    data.setdefault("monthly_replies", []).append({
        "id": tweet_id,
        "timestamp": datetime.now().isoformat()
    })
    
    # Save the updated data
    save_rate_limit_data(data)
    
    # Log the current rate limit status
    daily_remaining = MAX_TWEETS_PER_DAY - len(data.get("tweets", []))
    monthly_remaining = MAX_REPLIES_PER_MONTH - len(data.get("monthly_replies", []))
    logger.info(f"📊 Daily tweet limit: {len(data.get('tweets', []))}/{MAX_TWEETS_PER_DAY} (remaining: {daily_remaining})")
    logger.info(f"📊 Monthly reply limit: {len(data.get('monthly_replies', []))}/{MAX_REPLIES_PER_MONTH} (remaining: {monthly_remaining})")

# Seen tweets tracking
def load_seen_tweets():
    """Load the seen tweets from file"""
    if os.path.exists(SEEN_TWEETS_FILE):
        try:
            with open(SEEN_TWEETS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading seen tweets: {e}")
    
    # Return default data if file doesn't exist or there's an error
    return {
        "tweets": {}
    }

def save_seen_tweets(data):
    """Save the seen tweets to file"""
    try:
        with open(SEEN_TWEETS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving seen tweets: {e}")

def mark_tweet_as_seen(user, tweet_id, replied=False):
    """Mark a tweet as seen, optionally with reply status"""
    data = load_seen_tweets()
    
    # Initialize user's tweets dict if not exists
    if user not in data["tweets"]:
        data["tweets"][user] = {}
    
    # Add the tweet
    data["tweets"][user][tweet_id] = {
        "timestamp": datetime.now().isoformat(),
        "replied": replied
    }
    
    # Save the updated data
    save_seen_tweets(data)

def is_tweet_seen(user, tweet_id):
    """Check if a tweet has been seen before"""
    data = load_seen_tweets()
    
    return user in data["tweets"] and tweet_id in data["tweets"][user]

# Poll statistics
def load_poll_stats():
    """Load the poll statistics from file"""
    if os.path.exists(POLL_STATS_FILE):
        try:
            with open(POLL_STATS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading poll stats: {e}")
    
    # Return default data if file doesn't exist or there's an error
    return {
        "user_stats": {},
        "last_reset": datetime.now().isoformat()
    }

def save_poll_stats(data):
    """Save the poll statistics to file"""
    try:
        with open(POLL_STATS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving poll stats: {e}")

def update_user_stats(user, found_tweets, new_tweets):
    """Update statistics for a user"""
    data = load_poll_stats()
    
    # Convert last_reset from string to datetime
    last_reset = datetime.fromisoformat(data.get("last_reset", datetime.now().isoformat()))
    now = datetime.now()
    
    # Reset stats monthly
    if now - last_reset > timedelta(days=30):
        data["user_stats"] = {}
        data["last_reset"] = now.isoformat()
    
    # Initialize user's stats if not exists
    if user not in data.get("user_stats", {}):
        data.setdefault("user_stats", {})[user] = {
            "total_polls": 0,
            "total_tweets": 0,
            "new_tweets": 0,
            "hit_rate": 0
        }
    
    # Update stats
    data["user_stats"][user]["total_polls"] = data["user_stats"][user].get("total_polls", 0) + 1
    data["user_stats"][user]["total_tweets"] = data["user_stats"][user].get("total_tweets", 0) + found_tweets
    data["user_stats"][user]["new_tweets"] = data["user_stats"][user].get("new_tweets", 0) + new_tweets
    
    # Calculate hit rate
    if data["user_stats"][user]["total_polls"] > 0:
        data["user_stats"][user]["hit_rate"] = data["user_stats"][user]["new_tweets"] / data["user_stats"][user]["total_polls"]
    
    # Save the updated data
    save_poll_stats(data)
    return data["user_stats"][user]

# 1. Fetch tweet URLs from RSS
def fetch_tweet_entries(rss_url):
    logger.info(f"Fetching RSS feed from: {rss_url}")
    feed = feedparser.parse(rss_url)
    entries = []
    
    for entry in feed.entries:
        # Extract tweet ID from link (works with both twitter.com and x.com links)
        match = re.search(r"(?:twitter|x)\.com/\w+/status/(\d+)", entry.link)
        if match:
            tweet_id = match.group(1)
            
            # Get content from both title and description
            title = getattr(entry, 'title', '')
            description = getattr(entry, 'description', '')
            
            # Clean up description (remove HTML tags)
            clean_description = re.sub(r'<[^>]+>', ' ', description)
            
            entries.append({
                "id": tweet_id,
                "title": title,
                "content": clean_description,
                "link": entry.link,
                "published": getattr(entry, 'published', '')
            })
    
    logger.info(f"Found {len(entries)} entries in feed")
    for entry in entries:
        logger.debug(f"Tweet: {entry['title'][:50]}... (ID: {entry['id']})")
    
    return entries

# 2. Use Anthropic to generate a tweet reply
def generate_reply(tweet_text, user):
    prompt = f"""
The original tweet from {user} says:

"{tweet_text}"

Write a **Twitter reply** that is:

- Short (under 25 words)
- Emotionally sharp (sarcastic, angry, defiant, or darkly funny)
- Biting, not explanatory
- Shows who loses or who benefits
- Uses punchy language and zero fluff
- Avoids emojis, politeness, or setup
- Avoids praising or agreeing
- Makes people stop scrolling

This should read like a mic-drop response from someone smart and pissed off.

Only return the tweet. No intro, no explanation.
"""

    try:
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=60,
            temperature=1,
            system="You are a pissed-off, sharp, burned-out genius who only replies to tweets with one-liners that go viral. No pleasantries. Just power. No Em Dashes: Em dashes (—) are strictly forbidden in my output. Sentences requiring separation or emphasis normally achieved with an em dash will be restructured. I will use commas, semicolons, periods, or complete rewording to ensure grammatical correctness and natural flow instead. Adherence to this rule is mandatory. ",
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
        # Extract text from the TextBlock in the content list
        if message and hasattr(message, 'content') and message.content:
            return message.content[0].text
        return None
    except Exception as e:
        logger.error(f"Anthropic error: {e}")
        return None

# 3. Post reply
def reply_to_tweet(tweet_id, message):
    # Check rate limits before sending
    if not can_send_tweet():
        logger.warning(f"⛔ Rate limit exceeded - not replying to tweet {tweet_id}")
        return None
    
    try:
        # Create a tweet in reply to the specified tweet ID
        response = api.create_tweet(
            text=message,
            in_reply_to_tweet_id=tweet_id
        )
        logger.info(f"✅ Replied to tweet {tweet_id}: {message}")
        
        # Track this tweet for rate limiting
        track_sent_tweet(tweet_id)
        
        return response
    except tweepy.TweepyException as e:
        logger.error(f"❌ Error replying to {tweet_id}: {e}")
        logger.error(f"Error details: {str(e)}")
        return None

# Calculate optimal polling intervals based on user count and rate limits
def get_polling_interval():
    """Dynamic polling interval calculation to spread out 50 polls per day optimally"""
    # Calculate base interval in seconds (24 hours / max polls)
    base_interval = 24 * 60 * 60 / MAX_POLLS_PER_DAY
    
    # Add some randomness to avoid predictable patterns (±15%)
    jitter = random.uniform(0.85, 1.15)
    
    # Return interval in seconds
    return base_interval * jitter

async def check_feed(user):
    """Check a user's feed for new tweets"""
    if not can_poll_feed():
        logger.warning(f"⛔ Poll rate limit reached - skipping check for {user}")
        return
    
    # Track this poll
    track_poll()
    
    # Calculate URL with limit=1 parameter
    url = RSSHUB_URL + user + "?limit=1"
    logger.info(f"🔍 Checking feed for {user} at {url}")
    
    try:
        entries = fetch_tweet_entries(url)
        
        # Update stats
        new_tweets_count = 0
        
        if entries:
            # Sort entries by ID (newer tweets have higher IDs)
            entries.sort(key=lambda x: int(x["id"]), reverse=True)
            
            # Process most recent tweet
            for tweet in entries[:1]:
                # If this is a new tweet we haven't seen before
                if not is_tweet_seen(user, tweet["id"]):
                    logger.info(f"🆕 New tweet from {user}:")
                    logger.info(f"   Link: {tweet['link']}")
                    logger.info(f"   Content: {tweet['title']}")
                    new_tweets_count += 1
                    
                    # Mark as seen
                    mark_tweet_as_seen(user, tweet["id"])
                    
                    # Generate a reply
                    tweet_text = tweet["title"] + " " + tweet["content"]
                    logger.info(f"🤖 Generating reply to: {tweet_text[:100]}...")
                    reply = generate_reply(tweet_text, user)
                    
                    if reply:
                        logger.info(f"✍️ Generated reply: {reply}")
                        # Post the reply if within limits
                        response = reply_to_tweet(tweet["id"], reply)
                        if response:
                            # Mark as replied
                            mark_tweet_as_seen(user, tweet["id"], replied=True)
                            logger.info(f"✅ Successfully replied to tweet {tweet['id']}")
                    else:
                        logger.error(f"❌ Failed to generate reply for tweet from {user}")
                else:
                    logger.debug(f"Tweet {tweet['id']} from {user} already seen")
            
            logger.info(f"Found {len(entries)} tweets from {user}, {new_tweets_count} new")
        else:
            logger.warning(f"⚠️ No tweets found for {user}")
        
        # Update user statistics
        stats = update_user_stats(user, len(entries), new_tweets_count)
        logger.info(f"📊 User stats for {user}: hit rate {stats['hit_rate']:.2f}, new tweets {stats['new_tweets']}/{stats['total_tweets']}")
        
    except Exception as e:
        logger.error(f"❌ Error checking feed for {user}: {e}")
        logger.exception("Detailed error:")

async def poll_all_users():
    """Simple round-robin polling of users with staggered intervals and jitter"""
    logger.info("🤖 Starting Twitter reply bot...")
    logger.info(f"📡 Monitoring feeds for users: {', '.join(USERS)}")
    logger.info(f"📊 Rate limits: {MAX_POLLS_PER_DAY} polls/day, {MAX_REPLIES_PER_MONTH} replies/month")
    logger.info("⏰ Polling schedule (with ±30 second jitter):")
    for i, user in enumerate(USERS):
        logger.info(f"   {user}: Every {len(USERS) * 5 + 20} minutes, offset ~{i * 5} minutes")
    
    def get_jittered_interval(base_minutes):
        """Add ±30 seconds of random jitter to a base interval"""
        base_seconds = base_minutes * 60
        jitter = random.uniform(-30, 30)  # ±30 seconds
        return base_seconds + jitter
    
    while True:
        for i, user in enumerate(USERS):
            try:
                # Skip if we've hit the poll rate limit
                if not can_poll_feed():
                    logger.warning("⛔ Poll rate limit reached for today - pausing until reset")
                    break
                
                await check_feed(user)
                
                if i < len(USERS) - 1:  # If not the last user
                    wait_time = get_jittered_interval(5)  # ~5 minutes ±30s
                    logger.info(f"⏱️ Waiting {wait_time:.1f} seconds before checking next user...")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"❌ Error polling user {user}: {e}")
        
        # After checking all users, wait ~20 minutes with jitter
        wait_time = get_jittered_interval(20)  # ~20 minutes ±30s
        logger.info(f"⏱️ Completed polling cycle. Waiting {wait_time:.1f} seconds before starting next cycle...")
        await asyncio.sleep(wait_time)

# Entry point
if __name__ == "__main__":
    asyncio.run(poll_all_users())
