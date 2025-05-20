#!/bin/bash

# Update package list
sudo apt update
sudo apt upgrade -y

# Install required system dependencies
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    python3-pip \
    python3-venv \
    supervisor

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip3 install --upgrade pip
pip3 install \
    playwright \
    python-dotenv \
    feedparser \
    tweepy \
    anthropic \
    requests \
    asyncio

# Install Playwright browsers
playwright install chromium

# Create log directory
mkdir -p logs

# Create supervisor configuration
sudo tee /etc/supervisor/conf.d/twitbot.conf << EOF
[program:twitbot]
command=/home/ubuntu/twitbot/venv/bin/python /home/ubuntu/twitbot/app.py
directory=/home/ubuntu/twitbot
user=ubuntu
autostart=true
autorestart=true
stderr_logfile=/home/ubuntu/twitbot/logs/twitbot.err.log
stdout_logfile=/home/ubuntu/twitbot/logs/twitbot.out.log
environment=
    PATH="/home/ubuntu/twitbot/venv/bin:%(ENV_PATH)s",
    PYTHONPATH="/home/ubuntu/twitbot:%(ENV_PYTHONPATH)s"
EOF

# Create .env template file if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Twitter API Credentials
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

# Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_key

# RSSHub URL
RSSHUB_URL=your_rsshub_url

# Twitter Login Credentials (for cookie refresher)
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
EOF
    echo "Created .env template file. Please fill in your credentials."
fi

# Set correct permissions
chmod 600 .env
chmod +x app.py cookie_refresher.py

echo "Setup complete! Please:"
echo "1. Edit .env file with your credentials"
echo "2. Start the bot with: sudo supervisorctl reread && sudo supervisorctl update"
echo "3. Check status with: sudo supervisorctl status twitbot"
echo "4. View logs in the logs directory" 