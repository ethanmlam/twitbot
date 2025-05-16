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
MAX_REPLIES_PER_DAY = 16  # Maximum replies we'll make per day
MAX_POLLS_PER_DAY = 16    # Number of polling cycles per day
USERS_PER_CHECK = 3       # Number of users to check each time
MAX_REPLIES_PER_MONTH = 500  # Rate limit for replies per month
RSSHUB_URL = os.getenv("RSSHUB_URL")  # Use environment variable if available

# Test users - replace with your full set of users to monitor
USERS = [
    "elonmusk","sama","naval","pmarca","paulg","balajis","cdixon","bchesky","michael_saylor","jack",
"BarackObama","narendramodi","realDonaldTrump","AOC","HillaryClinton","tedcruz","chiproytx","JDVance1","GretaThunberg","Pontifex",
"rihanna","katyperry","taylorswift13","justinbieber","ladygaga","ArianaGrande","BTS_twt","billieeilish","edsheeran","shakira",
"Cristiano","KingJames","serenawilliams","TomBrady","MoSalah","KMbappe","LewisHamilton","rogerfederer","usainbolt","Simone_Biles",
"MrBeast","FabrizioRomano","dril","Arkunir","neiltyson","BillGates","Oprah","nytimes","BBCWorld","NASA"

]

# Calculate optimal intervals
BASE_INTERVAL = 24 * 60 * 60 / MAX_POLLS_PER_DAY  # Seconds between checks
MIN_INTERVAL = 5 * 60  # Minimum 5 minutes between checks

# Test mode configuration
TEST_MODE = False  # Set to True to prevent actual tweets
def set_test_mode(enabled=True):
    """Enable or disable test mode"""
    global TEST_MODE
    TEST_MODE = enabled
    logger.info(f"🧪 Test mode {'enabled' if enabled else 'disabled'}")

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
        "replies": [],           # Track actual replies made
        "polls": [],            # Track polling cycles
        "last_reset": datetime.now().isoformat(),
        "monthly_replies": [],
        "last_monthly_reset": datetime.now().isoformat()
    }

def save_rate_limit_data(data):
    """Save the rate limit data to file"""
    try:
        with open(RATE_LIMIT_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving rate limit data: {e}")

def can_make_reply():
    """Check if we can make another reply today"""
    data = load_rate_limit_data()
    
    # Convert timestamps from string to datetime
    last_reset = datetime.fromisoformat(data.get("last_reset", datetime.now().isoformat()))
    last_monthly_reset = datetime.fromisoformat(data.get("last_monthly_reset", datetime.now().isoformat()))
    now = datetime.now()
    
    # If it's been more than 24 hours since the last reset, reset the counters
    if now - last_reset > timedelta(hours=24):
        data["replies"] = []
        data["polls"] = []
        data["last_reset"] = now.isoformat()
        save_rate_limit_data(data)
    
    # If it's been more than a month since the last monthly reset, reset that counter
    if now - last_monthly_reset > timedelta(days=30):
        data["monthly_replies"] = []
        data["last_monthly_reset"] = now.isoformat()
        save_rate_limit_data(data)
    
    # Check if we're under the daily reply limit
    if len(data.get("replies", [])) >= MAX_REPLIES_PER_DAY:
        logger.warning(f"⚠️ Daily reply limit reached: {len(data['replies'])}/{MAX_REPLIES_PER_DAY} replies today")
        return False
    
    # Check if we're under the monthly limit
    if len(data.get("monthly_replies", [])) >= MAX_REPLIES_PER_MONTH:
        logger.warning(f"⚠️ Monthly reply limit reached: {len(data['monthly_replies'])}/{MAX_REPLIES_PER_MONTH} replies this month")
        return False
    
    return True

def can_poll_feed():
    """Check if we can do another polling cycle"""
    data = load_rate_limit_data()
    
    # Calculate completed cycles (every 3 users = 1 cycle)
    completed_cycles = len(data.get("polls", [])) // USERS_PER_CHECK
    
    # Check if we're under the daily cycle limit
    if completed_cycles >= MAX_POLLS_PER_DAY:
        logger.warning(f"⚠️ Daily cycle limit reached: {completed_cycles}/{MAX_POLLS_PER_DAY} cycles completed")
        return False
    
    return True

def track_poll():
    """Track that we completed a polling cycle"""
    data = load_rate_limit_data()
    
    # Get current polls count
    current_polls = len(data.get("polls", []))
    
    # Add the new poll with timestamp
    data.setdefault("polls", []).append({
        "timestamp": datetime.now().isoformat()
    })
    
    # Save the updated data
    save_rate_limit_data(data)
    
    # Calculate completed cycles (every 3 users = 1 cycle)
    completed_cycles = len(data.get("polls", [])) // USERS_PER_CHECK
    remaining_cycles = MAX_POLLS_PER_DAY - completed_cycles
    
    # Only log cycle completion when we finish a full set of users
    if len(data.get("polls", [])) % USERS_PER_CHECK == 0:
        logger.info(f"📊 Poll cycle status: {completed_cycles}/{MAX_POLLS_PER_DAY} cycles completed (remaining: {remaining_cycles})")
    else:
        users_in_current_cycle = len(data.get("polls", [])) % USERS_PER_CHECK
        logger.info(f"📊 Current cycle progress: {users_in_current_cycle}/{USERS_PER_CHECK} users checked")

def track_reply(tweet_id):
    """Track that we made a reply"""
    data = load_rate_limit_data()
    
    # Add the new reply with timestamp
    data.setdefault("replies", []).append({
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
    daily_remaining = MAX_REPLIES_PER_DAY - len(data.get("replies", []))
    monthly_remaining = MAX_REPLIES_PER_MONTH - len(data.get("monthly_replies", []))
    logger.info(f"📊 Daily reply limit: {len(data.get('replies', []))}/{MAX_REPLIES_PER_DAY} (remaining: {daily_remaining})")
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
def generate_reply(tweet_context, user):
    """Generate a sharp, one-liner Twitter reply using Claude with reduced token overhead"""

    system_prompt = (
        "You are a pissed-off, sharp, burned-out genius who only replies to tweets with brutal one-liners that go viral. "
        "No pleasantries. No setup. No fluff. Em dashes (—) are strictly forbidden. "
        "Use commas, or periods instead. Always rewrite to avoid them."
    )

    # Customize instructions based on tweet content
    if "picture" in tweet_context.lower():
        context_note = (
            "This tweet is just an image or media with no text. React like:\n"
            "- 'He really just dropped this and logged off.'\n"
            "- 'This didn’t have to go so hard.'"
        )
    else:
        context_note = "Respond to what they said, but be contrarian and sharp."

    prompt = f"""Tweet: {tweet_context}

Reply rules:
- Max 20 words
- Sarcastic, defiant, or darkly funny
- Punchy, no fluff
- No praise or agreement
- No emojis or setup
- Show who loses or benefits


{context_note}

Reply:"""

    try:
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=60,
            temperature=1,
            system=system_prompt,
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
        if message and hasattr(message, 'content') and message.content:
            return message.content[0].text.strip()
        return None
    except Exception as e:
        logger.error(f"Anthropic error: {e}")
        return None


# 3. Post reply
def reply_to_tweet(tweet_id, message):
    # Check rate limits before sending
    if not can_make_reply():
        logger.warning(f"⛔ Rate limit exceeded - not replying to tweet {tweet_id}")
        return None
    
    try:
        if TEST_MODE:
            logger.info(f"🧪 TEST MODE - Would reply to {tweet_id} with: {message}")
            return {"id": "test_" + str(tweet_id)}
        
        # Create a tweet in reply to the specified tweet ID
        response = api.create_tweet(
            text=message,
            in_reply_to_tweet_id=tweet_id
        )
        logger.info(f"✅ Replied to tweet {tweet_id}: {message}")
        
        # Track this tweet for rate limiting
        track_reply(tweet_id)
        
        return response
    except tweepy.TweepyException as e:
        logger.error(f"❌ Error replying to {tweet_id}: {e}")
        logger.error(f"Error details: {str(e)}")
        return None

# Calculate optimal polling intervals based on user count and rate limits
def get_polling_interval():
    """Calculate interval between checks with jitter"""
    # Base interval is 24 hours / number of checks
    base_interval = 24 * 60 * 60 / MAX_POLLS_PER_DAY  # seconds
    
    # Add random jitter (±15%)
    jitter_factor = random.uniform(0.85, 1.15)
    interval = base_interval * jitter_factor
    
    # Return interval in seconds
    return interval

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
                    
                    # Determine tweet type and content
                    title = tweet["title"].strip()
                    description = tweet["content"]

                    # First check title
                    if title:
                        tweet_type = "text"
                        prompt_context = f"The original tweet from {user} says:\n\n\"{title}\""
                    # If no title, check description for media
                    else:
                        tweet_type = "picture"
                        prompt_context = f"{user} posted a picture"
                    
                    logger.info(f"🤖 Generating reply to {tweet_type} tweet...")
                    reply = generate_reply(prompt_context, user)
                    
                    if reply:
                        logger.info(f"✍️ Generated reply: {reply}")
                        # Post the reply if within limits
                        response = reply_to_tweet(tweet["id"], reply)
                        if response:
                            # Mark as replied
                            mark_tweet_as_seen(user, tweet["id"], replied=True)
                            logger.info(f"✅ Successfully replied to {tweet_type} tweet {tweet['id']}")
                    else:
                        logger.error(f"❌ Failed to generate reply for {tweet_type} tweet from {user}")
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
    """Main polling loop that runs 16 times per day, checking 2 random users each time"""
    logger.info("🤖 Starting Twitter reply bot...")
    logger.info(f"📡 Monitoring pool of users: {', '.join(USERS)}")
    logger.info(f"📊 Schedule: {MAX_POLLS_PER_DAY} checks per day, {USERS_PER_CHECK} users per check")
    logger.info(f"⏰ Base interval between checks: {BASE_INTERVAL/60:.1f} minutes (±15% jitter)")
    
    while True:
        try:
            # Skip if we've hit the daily check limit
            if not can_poll_feed():
                logger.warning("⛔ Daily check limit reached - waiting until next reset")
                await asyncio.sleep(get_polling_interval())
                continue
            
            # Randomly select users to check
            users_to_check = random.sample(USERS, USERS_PER_CHECK)
            logger.info(f"🎲 Selected users for this check: {', '.join(users_to_check)}")
            
            # Check each selected user
            for user in users_to_check:
                await check_feed(user)
                
                # Small delay between users to avoid rate limits
                if user != users_to_check[-1]:  # Don't wait after last user
                    await asyncio.sleep(random.uniform(20, 50))
            
            # Calculate wait time until next check (base interval ±15%)
            wait_time = max(
                MIN_INTERVAL,  # Minimum 5 minutes
                random.uniform(BASE_INTERVAL * 0.85, BASE_INTERVAL * 1.15)
            )
            
            logger.info(f"⏱️ Completed check cycle. Next check in {wait_time/60:.1f} minutes")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"❌ Error in polling loop: {e}")
            logger.exception("Detailed error:")
            # Wait a bit before retrying on error
            await asyncio.sleep(MIN_INTERVAL)

# Entry point
if __name__ == "__main__":
    asyncio.run(poll_all_users())
