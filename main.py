#!/usr/bin/env python3
import logging
from dotenv import load_dotenv

from app.consumer import start_consumer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    try:
        logger.info("Starting classroom scheduler consumer")
        start_consumer()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
