import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_env_loading():
    # Get the absolute path to the .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    logger.debug(f"Looking for .env file at: {env_path}")

    # Check if file exists
    if not os.path.exists(env_path):
        logger.error(f".env file not found at {env_path}")
        return False

    logger.info(f".env file found at {env_path}")

    # Load environment variables
    load_dotenv(env_path)

    # Check if variables are loaded
    api_key = os.getenv('EXCHANGE_API_KEY')
    api_secret = os.getenv('EXCHANGE_API_SECRET')

    logger.debug(f"API Key loaded: {bool(api_key)}")
    logger.debug(f"API Secret loaded: {bool(api_secret)}")

    if not api_key or not api_secret:
        logger.error("API credentials not found in environment variables")
        return False

    logger.info("API credentials loaded successfully")
    return True

if __name__ == "__main__":
    test_env_loading() 