# Twitter RSS Reply Bot

This bot fetches tweets from an RSS feed containing tweets with "#buildinpublic", generates replies using Anthropic's Claude API, and posts them as replies.

## Setup

1. Create a `.env` file with your credentials:

```
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_SECRET=your_twitter_access_secret
ANTHROPIC_API_KEY=your_anthropic_api_key
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Bot

```bash
python app.py
```

## Running Tests

```bash
# Run all tests
python -m unittest test_app.py

# Run a specific test
python -m unittest test_app.TestTwitterBot.test_fetch_tweet_entries
```

The tests use mocks to avoid making actual API calls to Twitter, Anthropic or fetching real RSS feeds. 