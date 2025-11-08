#!/bin/bash
# Example usage scripts for Polymarket Scanner

echo "=================================="
echo "Polymarket Scanner - Examples"
echo "=================================="
echo ""

# Example 1: Initial setup and scan
echo "Example 1: Initial Scan"
echo "$ python polymarket_scanner.py scan"
echo ""

# Example 2: Find significant changes
echo "Example 2: Find markets with 5%+ changes in last hour"
echo "$ python polymarket_scanner.py changes"
echo ""

# Example 3: Custom thresholds
echo "Example 3: Find markets with 10%+ changes in last 30 minutes"
echo "$ python polymarket_scanner.py changes --threshold 10 --window 30"
echo ""

# Example 4: Top gainers
echo "Example 4: Top 20 gainers"
echo "$ python polymarket_scanner.py movers --limit 20 --direction up"
echo ""

# Example 5: Top losers
echo "Example 5: Top 10 losers in last 2 hours"
echo "$ python polymarket_scanner.py movers --limit 10 --direction down --window 120"
echo ""

# Example 6: Trending markets
echo "Example 6: Most volatile markets"
echo "$ python polymarket_scanner.py trending"
echo ""

# Example 7: Database stats
echo "Example 7: View database statistics"
echo "$ python polymarket_scanner.py stats"
echo ""

# Example 8: Continuous monitoring
echo "Example 8: Run continuous monitoring (every 5 minutes)"
echo "$ python run_scheduler.py --interval 300"
echo ""

# Example 9: Configuration
echo "Example 9: View current configuration"
echo "$ python polymarket_scanner.py config-info"
echo ""

echo "=================================="
echo "To run any example, copy and paste the command"
echo "=================================="
