"""Market scanner for fetching data from Polymarket API"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

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

    def fetch_simplified_markets(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Fetch simplified market data with embedded prices (faster)

        Args:
            active_only: If True, only return markets accepting orders
        """
        try:
            response = self.client.get_simplified_markets()
            markets = response.get('data', [])

            if active_only:
                markets = [m for m in markets if m.get('accepting_orders')]
                print(f"Filtered to {len(markets)} markets accepting orders")

            return markets
        except Exception as e:
            print(f"Error fetching simplified markets: {e}")
            return []

    def scan_and_store_with_prices(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Scan active markets and store with prices (optimized with batch fetching)

        This method:
        1. Gets simplified markets to find which are accepting orders
        2. Fetches full details in batches until all active markets found
        3. Stores prices from simplified endpoint
        4. Shows progress with visual indicators
        """
        print("\n[1/3] Finding active markets...")

        # Get simplified markets to find active ones
        simplified_markets = self.fetch_simplified_markets(active_only=True)

        if not simplified_markets:
            print("No active markets found!")
            return {'markets': 0, 'prices': 0}

        # Get condition IDs of active markets
        active_condition_ids = {m['condition_id'] for m in simplified_markets}
        total_active = len(active_condition_ids)
        print(f"✓ Found {total_active} active markets to fetch\n")

        # Fetch full market details in batches using pagination
        print(f"[2/3] Fetching full details with pagination...")

        active_markets = []
        found_ids = set()
        total_fetched = 0
        next_cursor = None
        batch_num = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task(
                f"[cyan]Searching for active markets...",
                total=total_active
            )

            while len(found_ids) < total_active:
                # Fetch next page of markets
                try:
                    if next_cursor is None:
                        response = self.client.get_markets()
                    else:
                        response = self.client.get_markets(next_cursor=next_cursor)

                    if 'data' not in response or not response['data']:
                        break

                    batch = response['data']
                    batch_num += 1
                    total_fetched += len(batch)

                    # Filter for active markets
                    for market in batch:
                        if market['condition_id'] in active_condition_ids:
                            if market['condition_id'] not in found_ids:
                                active_markets.append(market)
                                found_ids.add(market['condition_id'])
                                progress.update(task, completed=len(found_ids))

                    # Early exit if we found all active markets
                    if len(found_ids) >= total_active:
                        progress.update(task, description=f"[green]✓ Found all {total_active} active markets")
                        break

                    # Update progress
                    progress.update(
                        task,
                        description=f"[cyan]Found {len(found_ids)}/{total_active} (batch {batch_num}, scanned {total_fetched})"
                    )

                    # Check if there are more pages
                    next_cursor = response.get('next_cursor')
                    if not next_cursor:
                        # No more markets to fetch
                        progress.update(
                            task,
                            description=f"[yellow]Scanned all markets, found {len(found_ids)}/{total_active}"
                        )
                        break

                    # Rate limiting between batches
                    time.sleep(0.1)

                except Exception as e:
                    print(f"\n  Error fetching batch: {e}")
                    break

        print(f"\n✓ Fetched details for {len(active_markets)} active markets (scanned {total_fetched} total in {batch_num} batches)\n")

        # Apply user limit if specified
        if limit and len(active_markets) > limit:
            active_markets = active_markets[:limit]
            print(f"Limited to {limit} markets\n")

        # Create price lookup from simplified markets
        price_lookup = {}
        for sm in simplified_markets:
            if 'tokens' in sm:
                for token in sm['tokens']:
                    price_lookup[token['token_id']] = token.get('price')

        # Store markets with progress indicator
        print(f"[3/3] Storing {len(active_markets)} markets with prices...")

        markets_stored = 0
        prices_stored = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Storing markets...", total=len(active_markets))

            for market in active_markets:
                try:
                    # Store market
                    self.db.upsert_market(market)

                    # Store tokens with prices
                    if 'tokens' in market and isinstance(market['tokens'], list):
                        for token in market['tokens']:
                            # Store token
                            self.db.upsert_token(
                                token_id=token['token_id'],
                                condition_id=market['condition_id'],
                                outcome=token.get('outcome', 'UNKNOWN')
                            )

                            # Store price if available
                            token_id = token['token_id']
                            if token_id in price_lookup and price_lookup[token_id] is not None:
                                self.db.insert_price(
                                    token_id=token_id,
                                    condition_id=market['condition_id'],
                                    price=float(price_lookup[token_id])
                                )
                                prices_stored += 1

                    markets_stored += 1
                    progress.update(task, advance=1)

                except Exception as e:
                    print(f"\n  Error storing market {market.get('condition_id', 'unknown')[:20]}...: {e}")

        print(f"\n✓ Stored {markets_stored} markets and {prices_stored} prices")
        return {
            'markets': markets_stored,
            'prices': prices_stored
        }

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

        print(f"\nStoring {len(markets)} markets in database...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Storing markets...", total=len(markets))

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
                    progress.update(task, advance=1)

                except Exception as e:
                    print(f"\n  Error storing market {market.get('condition_id', 'unknown')}: {e}")

        print(f"\n✓ Stored {stored_count} markets")
        return stored_count

    def scan_and_store_prices(self, active_only: bool = True) -> int:
        """Scan current prices and store in database"""
        print("\nFetching current prices...")

        markets = self.db.get_all_active_markets() if active_only else []

        if not markets:
            print("No active markets found. Run scan_and_store_markets() first.")
            return 0

        # Count total tokens
        total_tokens = 0
        for market in markets:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT COUNT(*) as count FROM tokens WHERE condition_id = ?',
                    (market['condition_id'],)
                )
                total_tokens += cursor.fetchone()['count']

        stored_count = 0
        errors = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task(
                f"[cyan]Fetching prices for {len(markets)} markets...",
                total=total_tokens
            )

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

                    progress.update(task, advance=1)

                    # Rate limiting
                    time.sleep(0.05)

        print(f"\n✓ Stored {stored_count} price points ({errors} errors)")
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
