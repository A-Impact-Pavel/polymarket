# Polymarket Scanner System - Replit Setup

## Overview

This project is a comprehensive CLI application for scanning and monitoring prediction markets on Polymarket. It tracks price changes, identifies trending markets, and detects significant movements in real-time.

**Current Status**: ✅ Fully operational and running

## Recent Changes

- **2025-11-08**: Initial setup in Replit environment
  - Installed Python 3.11 and all dependencies
  - Configured workflow for continuous monitoring
  - Scanner is actively tracking 60,000+ markets from Polymarket

## Project Architecture

### Technology Stack
- **Language**: Python 3.11
- **Database**: SQLite (local file-based)
- **CLI Framework**: Click + Rich (for beautiful terminal output)
- **API Client**: py-clob-client (Polymarket's official Python SDK)

### Project Structure

```
polymarket/
├── src/
│   ├── __init__.py       # Package initialization
│   ├── config.py         # Configuration from environment variables
│   ├── database.py       # SQLite database operations
│   ├── scanner.py        # Polymarket API integration
│   ├── analyzer.py       # Price change detection and analysis
│   ├── cli.py            # CLI commands and interface
│   └── scheduler.py      # Continuous monitoring scheduler
├── polymarket_scanner.py # Main CLI entry point
├── run_scheduler.py      # Runs continuous monitoring
├── requirements.txt      # Python dependencies
├── .env                  # Configuration (created from .env.example)
└── polymarket_data.db    # SQLite database (auto-created)
```

### Key Components

1. **Scanner**: Fetches market data from Polymarket's CLOB API
2. **Database**: Stores markets, tokens, and historical price data
3. **Analyzer**: Detects price changes, identifies movers, and finds trends
4. **CLI**: Provides user-friendly command-line interface
5. **Scheduler**: Runs automatic scans every 5 minutes

## Replit Setup

### Workflow Configuration

The project runs a single workflow:
- **Name**: Polymarket Scanner
- **Command**: `python run_scheduler.py`
- **Type**: Console application
- **Function**: Continuously scans Polymarket every 5 minutes and stores price data

### Environment

- **Python Version**: 3.11 (installed via Replit modules)
- **Package Manager**: pip
- **Configuration**: `.env` file (based on `.env.example`)

### How It Works

1. **Automatic Monitoring**: The workflow runs `run_scheduler.py` which scans Polymarket every 5 minutes
2. **Data Storage**: All market data and price history is stored in `polymarket_data.db`
3. **CLI Access**: You can use the CLI commands at any time to query the data

## Using the CLI

The scanner provides several commands:

### View Statistics
```bash
python polymarket_scanner.py stats
```

### Find Significant Changes
```bash
# Show markets with 5%+ price changes in last hour
python polymarket_scanner.py changes

# Custom threshold and time window
python polymarket_scanner.py changes --threshold 10 --window 30
```

### See Top Movers
```bash
# Top 15 biggest movers
python polymarket_scanner.py movers

# Top gainers only
python polymarket_scanner.py movers --direction up
```

### Find Trending Markets
```bash
# Most volatile markets
python polymarket_scanner.py trending
```

### Get Market Details
```bash
python polymarket_scanner.py market <condition_id>
```

## Configuration

Settings are in the `.env` file:

- **DATABASE_PATH**: SQLite database location (default: `polymarket_data.db`)
- **SCAN_INTERVAL_SECONDS**: Time between scans (default: 300 = 5 minutes)
- **DEFAULT_CHANGE_THRESHOLD**: Alert threshold percentage (default: 5%)
- **TIME_WINDOW_MINUTES**: Lookback period for changes (default: 60 minutes)

## Workflow Management

### Restarting the Workflow

If you need to restart the scanner (e.g., after configuration changes):

1. Use the Replit interface to stop/start the workflow, or
2. The workflow automatically restarts when code or packages are updated

### Disabling Continuous Monitoring

If you want to stop the continuous scanning:

1. Stop the "Polymarket Scanner" workflow in the Replit interface
2. You can still use all CLI commands manually to query existing data
3. Restart the workflow when you want to resume monitoring

### Manual Scanning

You can always run a manual scan without the scheduler:

```bash
python polymarket_scanner.py scan
```

## Troubleshooting

### API Connection Issues

If the scanner fails to connect to Polymarket:

1. **Check API Status**: Verify that Polymarket's API is accessible
2. **Rate Limiting**: If you hit rate limits, increase `SCAN_INTERVAL_SECONDS` in `.env`
3. **Network Issues**: Temporary network problems will cause the current scan to fail, but the scheduler will retry on the next interval

### Database Issues

If you encounter database errors:

1. **Database Locked**: The workflow and manual CLI commands share the same database. SQLite can handle this, but if you see lock errors, try stopping the workflow temporarily
2. **Corrupted Database**: Delete `polymarket_data.db` and let the scanner rebuild it on the next run

### No Data Available

If CLI commands show no data:

1. **First Scan**: Make sure the scanner has completed at least one full scan
2. **Check Workflow Logs**: View the console output to see if scans are completing successfully
3. **Wait Time**: The initial scan can take a few minutes to fetch all markets

## User Preferences

None specified yet.

## Notes

- **Database**: SQLite database file is stored locally and persists between sessions
- **API Access**: Uses Polymarket's free API (no authentication required for read-only)
- **Rate Limits**: 1,000 API calls/hour (generous for 5-minute intervals)
- **No Frontend**: This is a pure CLI application - all interaction is via terminal
- **Continuous Operation**: The scheduler workflow runs continuously in the background
- **Maintenance**: Monitor workflow logs periodically to ensure stable operation
