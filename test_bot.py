import asyncio
import logging
from app import (
    check_feed,
    generate_reply,
    reply_to_tweet,
    USERS,
    MAX_REPLIES_PER_DAY,
    MAX_POLLS_PER_DAY,
    USERS_PER_CHECK,
    BASE_INTERVAL,
    MIN_INTERVAL,
    get_polling_interval,
    set_test_mode,
    can_make_reply,
    can_poll_feed
)
import random

# Setup test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
STEST_USERS = ["spydaris","aviderring","brian_armstrong"]
# Test configuration
TEST_USERS = ["elonmusk", "sama", "naval", "balajis", "brian_armstrong", "paulg", "rabois", "patrickc", "levelsio", "shl", "a16z", "cdixon", "mims", "gdb", "danabramov", "ryxcommar", "swyx", "sriramk", "delian", "davidmarcus", "mattyglesias", "pmarca", "benthompson", "karpathy", "geoffreyfowler", "masonclark", "sama", "chrislhayes", "lauralippay"]  # Small set of test users
TEST_CYCLES = 1  # Number of test cycles to run
TEST_INTERVAL = 60  # 1 minute between checks for testing

async def run_test_cycle():
    """Run a single test cycle"""
    try:
        # Skip if we've hit the daily cycle limit
        if not can_poll_feed():
            logger.warning("⛔ Daily cycle limit reached - skipping test cycle")
            return

        # Check all users in this cycle
        users_to_check = random.sample(TEST_USERS, USERS_PER_CHECK)
        logger.info(f"🧪 TEST: Starting cycle with users: {', '.join(users_to_check)}")
        
        # Check each selected user
        for i, user in enumerate(users_to_check, 1):
            logger.info(f"🧪 TEST: Checking user {user} ({i}/{USERS_PER_CHECK} in this cycle)")
            
            # Skip if we've hit the reply limit
            if not can_make_reply():
                logger.warning("⛔ Daily reply limit reached - skipping remaining users")
                break
            
            # Run the check
            await check_feed(user)
            
            # Small delay between users
            if i < USERS_PER_CHECK:  # Don't wait after last user
                delay = random.uniform(5, 10)  # Shorter delays for testing
                logger.info(f"🧪 TEST: Waiting {delay:.1f} seconds before next user")
                await asyncio.sleep(delay)
        
        logger.info("🧪 TEST: Full cycle completed")
        
    except Exception as e:
        logger.error(f"🧪 TEST ERROR: {e}")
        logger.exception("Detailed test error:")

async def run_test_suite():
    """Run the complete test suite"""
    # Enable test mode
    set_test_mode(True)
    
    logger.info("🧪 Starting bot test suite")
    logger.info(f"🧪 Will run {TEST_CYCLES} cycles with {TEST_INTERVAL} seconds between cycles")
    logger.info(f"🧪 Testing with users: {', '.join(TEST_USERS)}")
    logger.info(f"🧪 Each cycle will check {USERS_PER_CHECK} random users")
    
    for cycle in range(TEST_CYCLES):
        logger.info(f"\n🧪 Starting test cycle {cycle + 1}/{TEST_CYCLES}")
        await run_test_cycle()
        
        if cycle < TEST_CYCLES - 1:  # Don't wait after last cycle
            logger.info(f"🧪 Waiting {TEST_INTERVAL} seconds until next test cycle")
            await asyncio.sleep(TEST_INTERVAL)
    
    logger.info("\n🧪 Test suite completed!")

if __name__ == "__main__":
    try:
        asyncio.run(run_test_suite())
    except KeyboardInterrupt:
        logger.info("🧪 Test suite interrupted by user")
    except Exception as e:
        logger.error(f"🧪 Test suite failed: {e}")
        logger.exception("Detailed error:") 