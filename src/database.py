"""Database management for storing market data and price history"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from .config import Config


class Database:
    """Manages SQLite database for market data"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Config.get_db_path()
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Markets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS markets (
                    condition_id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    description TEXT,
                    end_date_iso TEXT,
                    game_start_time TEXT,
                    market_slug TEXT,
                    rewards_min_size REAL,
                    rewards_max_spread REAL,
                    enable_order_book INTEGER DEFAULT 1,
                    active INTEGER DEFAULT 1,
                    closed INTEGER DEFAULT 0,
                    archived INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tokens table (for YES/NO outcomes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    token_id TEXT PRIMARY KEY,
                    condition_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (condition_id) REFERENCES markets(condition_id)
                )
            ''')

            # Price history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id TEXT NOT NULL,
                    condition_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (token_id) REFERENCES tokens(token_id),
                    FOREIGN KEY (condition_id) REFERENCES markets(condition_id)
                )
            ''')

            # Create indexes for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_history_token_time
                ON price_history(token_id, timestamp DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_history_condition_time
                ON price_history(condition_id, timestamp DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_markets_active
                ON markets(active, closed)
            ''')

    def upsert_market(self, market_data: Dict[str, Any]):
        """Insert or update market data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO markets (
                    condition_id, question, description, end_date_iso,
                    game_start_time, market_slug, rewards_min_size,
                    rewards_max_spread, enable_order_book, active, closed, archived
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(condition_id) DO UPDATE SET
                    question = excluded.question,
                    description = excluded.description,
                    end_date_iso = excluded.end_date_iso,
                    game_start_time = excluded.game_start_time,
                    market_slug = excluded.market_slug,
                    active = excluded.active,
                    closed = excluded.closed,
                    archived = excluded.archived,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                market_data['condition_id'],
                market_data['question'],
                market_data.get('description'),
                market_data.get('end_date_iso'),
                market_data.get('game_start_time'),
                market_data.get('market_slug'),
                market_data.get('rewards', {}).get('min_size'),
                market_data.get('rewards', {}).get('max_spread'),
                market_data.get('enable_order_book', 1),
                market_data.get('active', 1),
                market_data.get('closed', 0),
                market_data.get('archived', 0)
            ))

    def upsert_token(self, token_id: str, condition_id: str, outcome: str):
        """Insert or update token data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO tokens (token_id, condition_id, outcome)
                VALUES (?, ?, ?)
            ''', (token_id, condition_id, outcome))

    def insert_price(self, token_id: str, condition_id: str, price: float, timestamp: Optional[str] = None):
        """Insert price data point"""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO price_history (token_id, condition_id, price, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (token_id, condition_id, price, timestamp))

    def get_latest_prices(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest prices for all active markets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT
                    m.condition_id,
                    m.question,
                    t.token_id,
                    t.outcome,
                    ph.price,
                    ph.timestamp
                FROM price_history ph
                INNER JOIN tokens t ON ph.token_id = t.token_id
                INNER JOIN markets m ON ph.condition_id = m.condition_id
                INNER JOIN (
                    SELECT token_id, MAX(timestamp) as max_timestamp
                    FROM price_history
                    GROUP BY token_id
                ) latest ON ph.token_id = latest.token_id AND ph.timestamp = latest.max_timestamp
                WHERE m.active = 1 AND m.closed = 0
                ORDER BY ph.timestamp DESC
                LIMIT ?
            ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_price_history(self, token_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get price history for a specific token"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    token_id,
                    condition_id,
                    price,
                    timestamp
                FROM price_history
                WHERE token_id = ?
                    AND timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp DESC
            ''', (token_id, hours))

            return [dict(row) for row in cursor.fetchall()]

    def get_market_by_condition_id(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Get market details by condition ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM markets WHERE condition_id = ?
            ''', (condition_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_active_markets(self) -> List[Dict[str, Any]]:
        """Get all active markets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM markets
                WHERE active = 1 AND closed = 0 AND archived = 0
                ORDER BY updated_at DESC
            ''')

            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM markets')
            total_markets = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM markets WHERE active = 1 AND closed = 0')
            active_markets = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM tokens')
            total_tokens = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM price_history')
            total_prices = cursor.fetchone()['count']

            return {
                'total_markets': total_markets,
                'active_markets': active_markets,
                'total_tokens': total_tokens,
                'total_price_points': total_prices
            }
