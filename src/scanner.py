"""Market scanner for fetching data from Polymarket API"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from .config import Config
from .database import Database


class PolymarketScanner:
    """Scans Polymarket for market data and prices"""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.client = ClobClient(
            host=Config.CLOB_API_URL,
            chain_id=Config.CHAIN_ID
        )

    def fetch_all_markets(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch all markets from Polymarket API with pagination

        Args:
            limit: Maximum number of markets to fetch. None = fetch all markets.
        """
        if limit:
            print(f"Fetching up to {limit} markets from Polymarket...")
        else:
            print("Fetching all markets from Polymarket...")

        markets_list = []
        next_cursor = None
        page = 1

        try:
            while True:
                if next_cursor is None:
                    response = self.client.get_markets()
                else:
                    response = self.client.get_markets(next_cursor=next_cursor)

                if 'data' not in response or not response['data']:
                    break

                # Check if we need to limit results
                if limit and len(markets_list) + len(response['data']) > limit:
                    remaining = limit - len(markets_list)
                    markets_list.extend(response['data'][:remaining])
                    print(f"  Fetched page {page}: {remaining} markets (total: {len(markets_list)})")
                    print(f"✓ Reached limit of {limit} markets")
                    break
                else:
                    markets_list.extend(response['data'])
                    print(f"  Fetched page {page}: {len(response['data'])} markets (total: {len(markets_list)})")

                next_cursor = response.get('next_cursor')

                if not next_cursor:
                    break

                # Stop if we've reached the limit
                if limit and len(markets_list) >= limit:
                    break

                page += 1
                time.sleep(0.1)  # Rate limiting

        except Exception as e:
            print(f"Error fetching markets: {e}")

        print(f"✓ Fetched {len(markets_list)} total markets")
        return markets_list

    def fetch_simplified_markets(self) -> List[Dict[str, Any]]:
        """Fetch simplified market data (faster, less detailed)"""
        try:
            response = self.client.get_simplified_markets()
            return response.get('data', [])
        except Exception as e:
            print(f"Error fetching simplified markets: {e}")
            return []

    def fetch_market_prices(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Fetch current price data for a specific token"""
        try:
            # Get midpoint price
            midpoint = self.client.get_midpoint(token_id)

            # Get buy/sell prices
            buy_price = self.client.get_price(token_id, side="BUY")
            sell_price = self.client.get_price(token_id, side="SELL")

            return {
                'token_id': token_id,
                'midpoint': float(midpoint) if midpoint else None,
                'buy_price': float(buy_price) if buy_price else None,
                'sell_price': float(sell_price) if sell_price else None,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            # Token might not have prices yet or be inactive
            return None

    def scan_and_store_markets(self, limit: Optional[int] = None) -> int:
        """Scan markets and store in database

        Args:
            limit: Maximum number of markets to fetch. None = fetch all markets.
        """
        markets = self.fetch_all_markets(limit=limit)
        stored_count = 0

        print("Storing markets in database...")

        for market in markets:
            try:
                # Store market
                self.db.upsert_market(market)

                # Store tokens (YES/NO outcomes)
                if 'tokens' in market and isinstance(market['tokens'], list):
                    for token in market['tokens']:
                        self.db.upsert_token(
                            token_id=token['token_id'],
                            condition_id=market['condition_id'],
                            outcome=token.get('outcome', 'UNKNOWN')
                        )

                stored_count += 1

            except Exception as e:
                print(f"Error storing market {market.get('condition_id', 'unknown')}: {e}")

        print(f"✓ Stored {stored_count} markets")
        return stored_count

    def scan_and_store_prices(self, active_only: bool = True) -> int:
        """Scan current prices and store in database"""
        print("Fetching current prices...")

        markets = self.db.get_all_active_markets() if active_only else []

        if not markets:
            print("No active markets found. Run scan_and_store_markets() first.")
            return 0

        stored_count = 0
        errors = 0

        for market in markets:
            condition_id = market['condition_id']

            # Get tokens for this market
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT token_id, outcome FROM tokens WHERE condition_id = ?',
                    (condition_id,)
                )
                tokens = [dict(row) for row in cursor.fetchall()]

            # Fetch and store price for each token
            for token in tokens:
                token_id = token['token_id']
                price_data = self.fetch_market_prices(token_id)

                if price_data and price_data['midpoint'] is not None:
                    try:
                        self.db.insert_price(
                            token_id=token_id,
                            condition_id=condition_id,
                            price=price_data['midpoint'],
                            timestamp=price_data['timestamp']
                        )
                        stored_count += 1
                    except Exception as e:
                        errors += 1

                # Rate limiting
                time.sleep(0.05)

        print(f"✓ Stored {stored_count} price points ({errors} errors)")
        return stored_count

    def full_scan(self, market_limit: Optional[int] = None) -> Dict[str, int]:
        """Perform a full scan: fetch markets and prices

        Args:
            market_limit: Maximum number of markets to fetch. None = fetch all markets.
        """
        print("\n" + "="*60)
        print("Starting full Polymarket scan...")
        if market_limit:
            print(f"Market limit: {market_limit}")
        print("="*60 + "\n")

        start_time = time.time()

        # Scan markets
        markets_count = self.scan_and_store_markets(limit=market_limit)

        # Scan prices
        prices_count = self.scan_and_store_prices()

        elapsed = time.time() - start_time

        print(f"\n✓ Scan completed in {elapsed:.2f} seconds")
        print(f"  Markets: {markets_count}")
        print(f"  Prices: {prices_count}")

        return {
            'markets': markets_count,
            'prices': prices_count,
            'elapsed': elapsed
        }
