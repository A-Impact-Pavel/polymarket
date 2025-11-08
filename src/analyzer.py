"""Analysis engine for detecting price changes and trends"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .database import Database
from .config import Config


@dataclass
class PriceChange:
    """Represents a significant price change"""
    condition_id: str
    question: str
    token_id: str
    outcome: str
    old_price: float
    new_price: float
    change_percent: float
    change_absolute: float
    time_window_minutes: int
    old_timestamp: str
    new_timestamp: str


class MarketAnalyzer:
    """Analyzes market data to detect significant changes"""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def calculate_price_change(
        self,
        token_id: str,
        time_window_minutes: int
    ) -> Optional[PriceChange]:
        """Calculate price change for a token over a time window"""

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Get latest price
            cursor.execute('''
                SELECT price, timestamp
                FROM price_history
                WHERE token_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (token_id,))

            latest = cursor.fetchone()
            if not latest:
                return None

            new_price = latest['price']
            new_timestamp = latest['timestamp']

            # Get price from time window ago
            cutoff_time = datetime.fromisoformat(new_timestamp) - timedelta(minutes=time_window_minutes)
            cursor.execute('''
                SELECT price, timestamp
                FROM price_history
                WHERE token_id = ?
                    AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (token_id, cutoff_time.isoformat()))

            old = cursor.fetchone()
            if not old:
                return None

            old_price = old['price']
            old_timestamp = old['timestamp']

            # Calculate change
            change_absolute = new_price - old_price
            change_percent = (change_absolute / old_price * 100) if old_price > 0 else 0

            # Get market and token info
            cursor.execute('''
                SELECT m.condition_id, m.question, t.outcome
                FROM tokens t
                JOIN markets m ON t.condition_id = m.condition_id
                WHERE t.token_id = ?
            ''', (token_id,))

            info = cursor.fetchone()
            if not info:
                return None

            return PriceChange(
                condition_id=info['condition_id'],
                question=info['question'],
                token_id=token_id,
                outcome=info['outcome'],
                old_price=old_price,
                new_price=new_price,
                change_percent=change_percent,
                change_absolute=change_absolute,
                time_window_minutes=time_window_minutes,
                old_timestamp=old_timestamp,
                new_timestamp=new_timestamp
            )

    def find_significant_changes(
        self,
        threshold_percent: Optional[float] = None,
        time_window_minutes: Optional[int] = None,
        limit: int = 50
    ) -> List[PriceChange]:
        """Find all tokens with significant price changes"""

        threshold = threshold_percent or Config.DEFAULT_CHANGE_THRESHOLD
        time_window = time_window_minutes or Config.TIME_WINDOW_MINUTES

        # Get all active tokens
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT t.token_id
                FROM tokens t
                JOIN markets m ON t.condition_id = m.condition_id
                WHERE m.active = 1 AND m.closed = 0
            ''')
            tokens = [row['token_id'] for row in cursor.fetchall()]

        # Calculate changes for all tokens
        significant_changes = []

        for token_id in tokens:
            change = self.calculate_price_change(token_id, time_window)

            if change and abs(change.change_percent) >= threshold:
                significant_changes.append(change)

        # Sort by absolute change percentage (descending)
        significant_changes.sort(key=lambda x: abs(x.change_percent), reverse=True)

        return significant_changes[:limit]

    def get_top_movers(
        self,
        time_window_minutes: Optional[int] = None,
        limit: int = 20,
        direction: str = 'both'  # 'up', 'down', or 'both'
    ) -> List[PriceChange]:
        """Get top price movers (biggest changes)"""

        time_window = time_window_minutes or Config.TIME_WINDOW_MINUTES

        # Get all active tokens
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT t.token_id
                FROM tokens t
                JOIN markets m ON t.condition_id = m.condition_id
                WHERE m.active = 1 AND m.closed = 0
            ''')
            tokens = [row['token_id'] for row in cursor.fetchall()]

        # Calculate changes
        changes = []
        for token_id in tokens:
            change = self.calculate_price_change(token_id, time_window)
            if change:
                changes.append(change)

        # Filter by direction
        if direction == 'up':
            changes = [c for c in changes if c.change_percent > 0]
            changes.sort(key=lambda x: x.change_percent, reverse=True)
        elif direction == 'down':
            changes = [c for c in changes if c.change_percent < 0]
            changes.sort(key=lambda x: x.change_percent)
        else:  # both
            changes.sort(key=lambda x: abs(x.change_percent), reverse=True)

        return changes[:limit]

    def get_market_summary(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive summary for a specific market"""

        market = self.db.get_market_by_condition_id(condition_id)
        if not market:
            return None

        # Get tokens and latest prices
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    t.token_id,
                    t.outcome,
                    ph.price,
                    ph.timestamp
                FROM tokens t
                LEFT JOIN (
                    SELECT token_id, price, timestamp
                    FROM price_history
                    WHERE (token_id, timestamp) IN (
                        SELECT token_id, MAX(timestamp)
                        FROM price_history
                        GROUP BY token_id
                    )
                ) ph ON t.token_id = ph.token_id
                WHERE t.condition_id = ?
            ''', (condition_id,))

            tokens = [dict(row) for row in cursor.fetchall()]

        # Calculate changes for each token
        token_changes = []
        for token in tokens:
            change = self.calculate_price_change(
                token['token_id'],
                Config.TIME_WINDOW_MINUTES
            )
            token_changes.append({
                'token_id': token['token_id'],
                'outcome': token['outcome'],
                'current_price': token['price'],
                'timestamp': token['timestamp'],
                'change': change
            })

        return {
            'market': market,
            'tokens': token_changes
        }

    def get_trending_markets(
        self,
        time_window_minutes: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get markets with the most volatility/activity"""

        time_window = time_window_minutes or Config.TIME_WINDOW_MINUTES

        # Get all significant changes
        changes = self.find_significant_changes(
            threshold_percent=1,  # Lower threshold to capture more activity
            time_window_minutes=time_window,
            limit=1000
        )

        # Group by market
        market_changes = {}
        for change in changes:
            cid = change.condition_id
            if cid not in market_changes:
                market_changes[cid] = {
                    'condition_id': cid,
                    'question': change.question,
                    'max_change': 0,
                    'total_volatility': 0,
                    'num_changes': 0
                }

            market_changes[cid]['max_change'] = max(
                market_changes[cid]['max_change'],
                abs(change.change_percent)
            )
            market_changes[cid]['total_volatility'] += abs(change.change_percent)
            market_changes[cid]['num_changes'] += 1

        # Sort by total volatility
        trending = sorted(
            market_changes.values(),
            key=lambda x: x['total_volatility'],
            reverse=True
        )

        return trending[:limit]
