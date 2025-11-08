#!/usr/bin/env python3
"""
Polymarket Scanner - Continuous Scheduler

Runs the scanner continuously at regular intervals.
"""

import sys
import argparse
from src.scheduler import ScanScheduler
from src.config import Config


def main():
    parser = argparse.ArgumentParser(
        description='Run Polymarket scanner continuously'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=None,
        help=f'Scan interval in seconds (default: {Config.SCAN_INTERVAL_SECONDS})'
    )

    args = parser.parse_args()

    scheduler = ScanScheduler()

    try:
        scheduler.start(interval_seconds=args.interval)
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        sys.exit(0)


if __name__ == '__main__':
    main()
