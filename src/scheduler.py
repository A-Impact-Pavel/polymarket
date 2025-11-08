"""Scheduler for automated market scanning"""

import time
import schedule
from datetime import datetime
from typing import Optional

from .scanner import PolymarketScanner
from .database import Database
from .config import Config


class ScanScheduler:
    """Manages scheduled scans of Polymarket"""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.scanner = PolymarketScanner(self.db)
        self.running = False

    def scan_job(self):
        """Job to be executed on schedule"""
        print("\n" + "="*60)
        print(f"Scheduled scan starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        try:
            result = self.scanner.full_scan()
            print(f"\n✓ Scheduled scan completed successfully")
            print(f"  Markets updated: {result['markets']}")
            print(f"  Prices recorded: {result['prices']}")
            print(f"  Elapsed time: {result['elapsed']:.2f}s")
        except Exception as e:
            print(f"\n✗ Scheduled scan failed: {e}")

    def start(self, interval_seconds: Optional[int] = None):
        """Start the scheduler"""
        interval = interval_seconds or Config.SCAN_INTERVAL_SECONDS

        print("\n" + "="*60)
        print("Polymarket Scanner - Continuous Mode")
        print("="*60)
        print(f"\nScan interval: {interval} seconds ({interval/60:.1f} minutes)")
        print(f"Database: {Config.get_db_path()}")
        print("\nPress Ctrl+C to stop\n")

        # Schedule the job
        schedule.every(interval).seconds.do(self.scan_job)

        # Run initial scan immediately
        self.scan_job()

        # Start the scheduler loop
        self.running = True
        print("\n" + "-"*60)
        print("Scheduler started. Waiting for next scan...")
        print("-"*60 + "\n")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping scheduler...")
            self.running = False

    def stop(self):
        """Stop the scheduler"""
        self.running = False
