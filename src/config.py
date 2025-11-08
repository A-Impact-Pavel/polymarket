"""Configuration management for Polymarket Scanner"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'polymarket_data.db')

    # Scanner settings
    SCAN_INTERVAL_SECONDS = int(os.getenv('SCAN_INTERVAL_SECONDS', '300'))
    DEFAULT_CHANGE_THRESHOLD = float(os.getenv('DEFAULT_CHANGE_THRESHOLD', '5'))
    TIME_WINDOW_MINUTES = int(os.getenv('TIME_WINDOW_MINUTES', '60'))

    # API settings
    CLOB_API_URL = os.getenv('CLOB_API_URL', 'https://clob.polymarket.com')
    CHAIN_ID = int(os.getenv('CHAIN_ID', '137'))

    @classmethod
    def get_db_path(cls) -> Path:
        """Get absolute path to database file"""
        if os.path.isabs(cls.DATABASE_PATH):
            return Path(cls.DATABASE_PATH)
        return cls.BASE_DIR / cls.DATABASE_PATH
