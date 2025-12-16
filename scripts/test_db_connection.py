import logging
import os
from health_platform.utils.db import SnowflakeConnection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_connection")

def test_connection():
    logger.info("Attempting to connect to Snowflake...")
    logger.info(f"Account: {os.environ.get('DB_ACCOUNT')}")
    logger.info(f"User: {os.environ.get('DB_USER')}")
    
    try:
        conn_wrapper = SnowflakeConnection()
        conn = conn_wrapper.get_connection()
        logger.info("Connection successful!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT current_version()")
        version = cursor.fetchone()[0]
        logger.info(f"Snowflake Version: {version}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    if test_connection():
        exit(0)
    else:
        exit(1)
