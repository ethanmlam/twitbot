# Twitter Reply Bot

An intelligent Twitter bot that monitors RSS feeds for tweets from specified users and automatically generates and posts replies.

## Key Features

- **Intelligent Polling Strategy**: Optimizes 50 polls/day allocation for maximum tweet discovery
- **Adaptive Time Windows**: Increases polling frequency during users' active hours
- **User Activity Weighting**: Prioritizes users based on their typical tweet frequency
- **Rate Limiting**: Enforces limits of 50 polls/day and 500 replies/month
- **Smart Reply Generation**: Uses Anthropic Claude model to generate contextually relevant, engaging replies
- **Persistence**: Tracks seen tweets and statistics across restarts

## Architecture

The bot consists of these main components:

1. **RSS Feed Polling**: Monitors custom RSSHub feeds for specified Twitter users
2. **Tweet Detection**: Identifies new tweets and avoids duplicates
3. **Reply Generation**: Uses Claude AI to create contextual responses
4. **Rate Limiting**: Manages API usage within specified constraints
5. **Statistics**: Tracks efficiency metrics to optimize polling strategy

## Polling Strategy

The bot employs a sophisticated polling strategy designed to maximize unique tweet discovery while respecting rate limits:

- **Time-Based Targeting**: Increases polling probability during each user's active hours
- **User Weighting**: Allocates more polling slots to high-activity users
- **Dynamic Intervals**: Adjusts polling frequency based on 50 polls/day limit
- **Randomized Scheduling**: Prevents predictable patterns to avoid Twitter detection
- **Adaptive Learning**: Maintains hit rate statistics to optimize future polling

## Configuration

Key configuration parameters:

- `MAX_POLLS_PER_DAY`: 50 (API constraint)
- `MAX_REPLIES_PER_MONTH`: 500 (API constraint)
- `MAX_TWEETS_PER_DAY`: 16 (Twitter rate limit)
- `USERS`: List of Twitter users to monitor
- `USER_WEIGHTS`: Relative polling frequency weights for each user
- `ACTIVE_WINDOWS`: UTC time windows when users are most active

## Setup

1. Install required packages: `pip install -r requirements.txt`
2. Create a `.env` file with your API keys (see `.env.example`)
3. Set up RSSHub instance for Twitter feeds
4. Run the bot: `python app.py`

## Environment Variables

```
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_SECRET=your_twitter_access_secret
ANTHROPIC_API_KEY=your_anthropic_api_key
RSSHUB_URL=https://your-rsshub-instance.com/twitter/user/
```

## Statistical Insights

The bot maintains detailed statistics on:
- Poll hit rates (new tweets discovered per poll)
- User activity patterns
- Optimal polling times
- Reply effectiveness

This data continuously improves the polling strategy over time.

## Running Tests

```bash
# Run all tests
python -m unittest test_app.py

# Run a specific test
python -m unittest test_app.TestTwitterBot.test_fetch_tweet_entries
```

The tests use mocks to avoid making actual API calls to Twitter, Anthropic or fetching real RSS feeds. 