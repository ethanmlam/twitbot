# Twitter Reply Bot

An intelligent Twitter bot that monitors RSS feeds for tweets from specified users and automatically generates and posts replies using Claude AI.

## Features

- Monitors a pool of Twitter users via RSS feeds
- Runs 16 checks per day, selecting 2 random users each time
- Uses Claude AI to generate contextual replies
- Avoids duplicate replies
- Rate limiting and error handling
- Detailed logging

## Setup

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_SECRET=your_twitter_access_token_secret
ANTHROPIC_API_KEY=your_anthropic_api_key
RSSHUB_URL=https://your-rsshub-instance.com/twitter/user/
```

## Testing

The bot includes a test suite to verify functionality before deployment:

1. **Quick Test (3 cycles)**
```bash
python test_bot.py
```
This will:
- Run 3 test cycles with 1-minute intervals
- Use a small set of test users (elonmusk, sama)
- Log all actions to test_bot.log
- Prevent actual tweets from being sent

2. **Monitor the Logs**
- Check `test_bot.log` for detailed test output
- Verify RSS feed fetching
- Review Claude's generated replies
- Confirm rate limiting works

3. **Test Output**
The test suite will show:
- User selection for each cycle
- RSS feed fetch results
- Generated replies (without posting)
- Rate limit tracking
- Any errors or issues

4. **What to Look For**
- Successful RSS feed fetching
- Reasonable Claude replies
- Proper rate limiting
- Error handling
- Log clarity

4. **Production Deployment**
After testing, deploy to your Oracle VM:

1. Transfer files to VM
2. Set up environment
3. Start the bot:
```bash
python app.py
```

## Monitoring

- Check `bot.log` for operation details
- Monitor rate limits and API usage
- Review generated replies

## Configuration

Key settings in `app.py`:
- `MAX_CHECKS_PER_DAY`: 16 checks per day
- `USERS_PER_CHECK`: 2 users per check
- `BASE_INTERVAL`: ~90 minutes between checks
- `MIN_INTERVAL`: 5 minutes minimum between checks

## Troubleshooting

Common issues and solutions:
- RSS feed errors: Check RSSHUB_URL configuration
- Rate limits: Monitor bot.log for limit warnings
- API errors: Verify credentials in .env
- Connection issues: Check network connectivity

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