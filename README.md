# Polymarket Scanner System

A comprehensive system for scanning [Polymarket](https://polymarket.com/) prediction markets and tracking price changes over time. Detect significant movements, identify trending markets, and monitor prediction changes with customizable thresholds.

## Features

- **Market Scanning**: Automatically fetch and store all Polymarket markets and prices
- **Change Detection**: Identify markets with significant price changes (e.g., X% in Y minutes)
- **Price History**: Track historical price data in a local SQLite database
- **Top Movers**: Find markets with the biggest price movements
- **Trending Markets**: Discover the most volatile/active markets
- **Continuous Monitoring**: Run scheduled scans at regular intervals
- **Rich CLI**: Beautiful command-line interface with tables and colored output

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Setup

1. **Clone or navigate to the repository**:
```bash
cd /home/user/polymarket
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment** (optional):
```bash
cp .env.example .env
# Edit .env to customize settings
```

## Quick Start

### 1. Initial Scan

**⚡ RECOMMENDED: Scan only active markets (fast - ~3 seconds!)**

```bash
# Scan ONLY markets accepting orders (~13 active markets)
python polymarket_scanner.py scan-active
```

This will:
- Find markets currently accepting orders (~13 markets)
- Fetch full details using smart batch fetching
- Store prices directly from API
- **Complete in ~3 seconds** with progress bars

**Alternative: Scan with limit (for testing or historical data)**

```bash
# Scan with limit (recommended for testing)
python polymarket_scanner.py scan --limit 100

# Or scan all markets (takes 30+ minutes - 60,000+ markets!)
python polymarket_scanner.py scan
```

**Performance Comparison:**
- `scan-active`: ~3 seconds, 13 active markets, includes prices ⚡
- `scan --limit 100`: ~9 seconds, 100 markets (mostly old/closed)
- `scan --limit 10000`: ~10 minutes, 10,000 markets (mostly old/closed)

### 2. Check for Changes

Find markets with significant price changes:

```bash
# Show changes >= 5% in the last 60 minutes (default)
python polymarket_scanner.py changes

# Custom threshold and time window
python polymarket_scanner.py changes --threshold 10 --window 30
```

### 3. View Top Movers

See the biggest price movements:

```bash
# Top 15 movers (any direction)
python polymarket_scanner.py movers

# Top 20 gainers only
python polymarket_scanner.py movers --limit 20 --direction up

# Top 10 losers in last 2 hours
python polymarket_scanner.py movers --limit 10 --direction down --window 120
```

### 4. Find Trending Markets

Discover the most volatile markets:

```bash
# Most volatile markets
python polymarket_scanner.py trending

# Custom time window and limit
python polymarket_scanner.py trending --window 30 --limit 15
```

### 5. Market Details

Get detailed information about a specific market:

```bash
python polymarket_scanner.py market <condition_id>
```

## Continuous Monitoring

Run the scanner continuously to track changes over time:

```bash
# Run with default interval (5 minutes)
python run_scheduler.py

# Custom interval (e.g., every 2 minutes)
python run_scheduler.py --interval 120
```

Press `Ctrl+C` to stop the scheduler.

## CLI Commands Reference

### `scan`
Perform a full scan of Polymarket markets and prices.

```bash
python polymarket_scanner.py scan [OPTIONS]

Options:
  -l, --limit INTEGER  Maximum number of markets to fetch (default: all)
```

**Examples:**
```bash
# Scan 100 markets (recommended for testing)
python polymarket_scanner.py scan --limit 100

# Scan all markets
python polymarket_scanner.py scan
```

### `scan-active` ⚡
Scan only active markets accepting orders (FAST - ~3 seconds).

```bash
python polymarket_scanner.py scan-active [OPTIONS]

Options:
  -l, --limit INTEGER  Maximum number of active markets to fetch
```

**Features:**
- Smart batch fetching (stops early when all active markets found)
- Progress bars for all stages
- Includes prices directly from API
- ~97% faster than full scan (3s vs 2+ minutes)

**Example:**
```bash
# Scan all active markets (recommended!)
python polymarket_scanner.py scan-active
```

### `changes`
Show significant price changes.

```bash
python polymarket_scanner.py changes [OPTIONS]

Options:
  -t, --threshold FLOAT    Change threshold percentage (default: 5)
  -w, --window INTEGER     Time window in minutes (default: 60)
  -l, --limit INTEGER      Maximum number of results (default: 20)
```

### `movers`
Show top price movers.

```bash
python polymarket_scanner.py movers [OPTIONS]

Options:
  -w, --window INTEGER           Time window in minutes (default: 60)
  -l, --limit INTEGER            Maximum number of results (default: 15)
  -d, --direction [up|down|both] Filter by direction (default: both)
```

### `trending`
Show trending markets (most volatile).

```bash
python polymarket_scanner.py trending [OPTIONS]

Options:
  -w, --window INTEGER  Time window in minutes (default: 60)
  -l, --limit INTEGER   Maximum number of results (default: 10)
```

### `market`
Show detailed information for a specific market.

```bash
python polymarket_scanner.py market CONDITION_ID
```

### `stats`
Show database statistics.

```bash
python polymarket_scanner.py stats
```

### `config-info`
Show current configuration.

```bash
python polymarket_scanner.py config-info
```

## Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Database
DATABASE_PATH=polymarket_data.db

# Scanner Settings
SCAN_INTERVAL_SECONDS=300        # Scan every 5 minutes
DEFAULT_CHANGE_THRESHOLD=5       # Alert on 5% change
TIME_WINDOW_MINUTES=60           # Check changes within last 60 minutes
DEFAULT_MARKET_LIMIT=0           # Max markets to fetch (0 = no limit, e.g., 100 for testing)

# API Settings
CLOB_API_URL=https://clob.polymarket.com
CHAIN_ID=137                     # Polygon Mainnet
```

## Use Cases

### Example 1: Monitor Election Markets

Track price movements in political prediction markets:

```bash
# Scan every 5 minutes
python run_scheduler.py --interval 300

# In another terminal, check for significant changes
python polymarket_scanner.py changes --threshold 3
```

### Example 2: Find Quick Movers

Detect rapid price changes:

```bash
# Look for 10%+ changes in the last 15 minutes
python polymarket_scanner.py changes --threshold 10 --window 15
```

### Example 3: Daily Market Summary

Get an overview of market activity:

```bash
# Most active markets in the last 24 hours
python polymarket_scanner.py trending --window 1440 --limit 20

# Biggest movers
python polymarket_scanner.py movers --window 1440 --limit 20
```

## Architecture

```
polymarket/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── config.py             # Configuration management
│   ├── database.py           # SQLite database operations
│   ├── scanner.py            # Polymarket API scanner
│   ├── analyzer.py           # Price change analysis
│   ├── cli.py                # Command-line interface
│   └── scheduler.py          # Automated scanning
├── polymarket_scanner.py     # Main CLI entry point
├── run_scheduler.py          # Continuous scheduler
├── requirements.txt          # Python dependencies
├── .env.example              # Example configuration
└── README.md                 # This file
```

### Components

1. **Scanner** (`scanner.py`): Fetches market data and prices from Polymarket's CLOB API
2. **Database** (`database.py`): Stores markets, tokens, and price history in SQLite
3. **Analyzer** (`analyzer.py`): Detects price changes and calculates trends
4. **CLI** (`cli.py`): User-friendly command-line interface using Click and Rich
5. **Scheduler** (`scheduler.py`): Runs scans at regular intervals
6. **Config** (`config.py`): Manages configuration from environment variables

## Database Schema

### Tables

- **markets**: Stores market information (questions, end dates, status)
- **tokens**: Stores outcome tokens (YES/NO for each market)
- **price_history**: Time-series price data for all tokens

### Indexes

Optimized indexes for fast queries:
- Token + timestamp (for price history lookups)
- Condition ID + timestamp (for market analysis)
- Active markets (for filtering)

## API Information

This system uses the [Polymarket CLOB API](https://docs.polymarket.com/):

- **Base URL**: https://clob.polymarket.com
- **Official Python Client**: [py-clob-client](https://github.com/Polymarket/py-clob-client)
- **Rate Limits**: 1,000 calls/hour for free tier (non-trading queries)
- **No Authentication Required**: For read-only market data access

## Troubleshooting

### No changes detected

Run a fresh scan first:
```bash
python polymarket_scanner.py scan
```

Then wait a few minutes and run another scan to build price history:
```bash
python polymarket_scanner.py scan
```

Now you can check for changes:
```bash
python polymarket_scanner.py changes
```

### Database locked errors

If you're running the scheduler and CLI simultaneously, SQLite might lock. This is rare but can happen. Solution:
- Stop the scheduler
- Run your CLI command
- Restart the scheduler

### API rate limiting

If you hit rate limits:
- Increase `SCAN_INTERVAL_SECONDS` to reduce frequency
- The free tier allows 1,000 calls/hour, which is generous for most use cases

## Advanced Usage

### Custom Database Location

Set a custom database path:

```bash
export DATABASE_PATH=/path/to/custom/database.db
python polymarket_scanner.py scan
```

### Programmatic Access

Use the modules directly in your Python code:

```python
from src.scanner import PolymarketScanner
from src.analyzer import MarketAnalyzer

# Scan markets
scanner = PolymarketScanner()
scanner.full_scan()

# Find changes
analyzer = MarketAnalyzer()
changes = analyzer.find_significant_changes(threshold_percent=5, time_window_minutes=60)

for change in changes:
    print(f"{change.question}: {change.change_percent:.2f}%")
```

## Contributing

Contributions are welcome! Areas for improvement:

- WebSocket support for real-time updates
- Email/SMS notifications for significant changes
- Web dashboard for visualization
- Export data to CSV/JSON
- Support for market-specific filters

## License

This project is open source and available under the MIT License.

## Disclaimer

This tool is for informational purposes only. It is not financial advice. Always do your own research before making any trading decisions.

## Resources

- [Polymarket](https://polymarket.com/)
- [Polymarket API Documentation](https://docs.polymarket.com/)
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)
