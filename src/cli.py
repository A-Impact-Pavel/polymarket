"""Command-line interface for Polymarket Scanner"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from datetime import datetime

from .scanner import PolymarketScanner
from .analyzer import MarketAnalyzer
from .database import Database
from .config import Config

console = Console()


@click.group()
def cli():
    """Polymarket Scanner - Track prediction market changes"""
    pass


@cli.command()
def scan():
    """Perform a full scan of Polymarket markets and prices"""
    scanner = PolymarketScanner()

    with console.status("[bold green]Scanning Polymarket..."):
        result = scanner.full_scan()

    console.print(Panel(
        f"[green]✓[/green] Scan completed!\n\n"
        f"Markets: {result['markets']}\n"
        f"Prices: {result['prices']}\n"
        f"Time: {result['elapsed']:.2f}s",
        title="Scan Results",
        border_style="green"
    ))


@cli.command()
@click.option('--threshold', '-t', default=None, type=float, help='Change threshold percentage')
@click.option('--window', '-w', default=None, type=int, help='Time window in minutes')
@click.option('--limit', '-l', default=20, type=int, help='Maximum number of results')
def changes(threshold, window, limit):
    """Show significant price changes"""
    analyzer = MarketAnalyzer()

    threshold = threshold or Config.DEFAULT_CHANGE_THRESHOLD
    window = window or Config.TIME_WINDOW_MINUTES

    console.print(f"\n[bold]Searching for changes ≥ {threshold}% in last {window} minutes...[/bold]\n")

    with console.status("[bold yellow]Analyzing markets..."):
        significant_changes = analyzer.find_significant_changes(
            threshold_percent=threshold,
            time_window_minutes=window,
            limit=limit
        )

    if not significant_changes:
        console.print("[yellow]No significant changes found.[/yellow]")
        return

    # Create table
    table = Table(title=f"Significant Price Changes (≥{threshold}%)", show_header=True, header_style="bold magenta")
    table.add_column("Market", style="cyan", width=50)
    table.add_column("Outcome", style="white")
    table.add_column("Old Price", justify="right")
    table.add_column("New Price", justify="right")
    table.add_column("Change", justify="right")

    for change in significant_changes:
        # Color code based on direction
        if change.change_percent > 0:
            change_str = f"[green]+{change.change_percent:.2f}%[/green]"
        else:
            change_str = f"[red]{change.change_percent:.2f}%[/red]"

        table.add_row(
            change.question[:50] + "..." if len(change.question) > 50 else change.question,
            change.outcome,
            f"{change.old_price:.4f}",
            f"{change.new_price:.4f}",
            change_str
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(significant_changes)} significant changes[/dim]")


@cli.command()
@click.option('--window', '-w', default=None, type=int, help='Time window in minutes')
@click.option('--limit', '-l', default=15, type=int, help='Maximum number of results')
@click.option('--direction', '-d', type=click.Choice(['up', 'down', 'both']), default='both', help='Filter by direction')
def movers(window, limit, direction):
    """Show top price movers"""
    analyzer = MarketAnalyzer()

    window = window or Config.TIME_WINDOW_MINUTES

    console.print(f"\n[bold]Top {limit} movers in last {window} minutes ({direction})...[/bold]\n")

    with console.status("[bold yellow]Analyzing markets..."):
        top_movers = analyzer.get_top_movers(
            time_window_minutes=window,
            limit=limit,
            direction=direction
        )

    if not top_movers:
        console.print("[yellow]No price movements found.[/yellow]")
        return

    # Create table
    table = Table(title=f"Top {direction.capitalize()} Movers", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Market", style="cyan", width=45)
    table.add_column("Outcome", style="white", width=8)
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")

    for idx, change in enumerate(top_movers, 1):
        # Color code based on direction
        if change.change_percent > 0:
            change_str = f"[green]+{change.change_percent:.2f}%[/green]"
        else:
            change_str = f"[red]{change.change_percent:.2f}%[/red]"

        table.add_row(
            str(idx),
            change.question[:45] + "..." if len(change.question) > 45 else change.question,
            change.outcome,
            f"{change.new_price:.4f}",
            change_str
        )

    console.print(table)


@cli.command()
@click.option('--window', '-w', default=None, type=int, help='Time window in minutes')
@click.option('--limit', '-l', default=10, type=int, help='Maximum number of results')
def trending(window, limit):
    """Show trending markets (most volatile)"""
    analyzer = MarketAnalyzer()

    window = window or Config.TIME_WINDOW_MINUTES

    console.print(f"\n[bold]Most volatile markets in last {window} minutes...[/bold]\n")

    with console.status("[bold yellow]Analyzing markets..."):
        trending_markets = analyzer.get_trending_markets(
            time_window_minutes=window,
            limit=limit
        )

    if not trending_markets:
        console.print("[yellow]No trending markets found.[/yellow]")
        return

    # Create table
    table = Table(title="Trending Markets", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Market", style="cyan", width=55)
    table.add_column("Max Change", justify="right")
    table.add_column("Total Volatility", justify="right")

    for idx, market in enumerate(trending_markets, 1):
        table.add_row(
            str(idx),
            market['question'][:55] + "..." if len(market['question']) > 55 else market['question'],
            f"{market['max_change']:.2f}%",
            f"{market['total_volatility']:.2f}%"
        )

    console.print(table)


@cli.command()
@click.argument('condition_id')
def market(condition_id):
    """Show detailed information for a specific market"""
    analyzer = MarketAnalyzer()

    with console.status("[bold yellow]Fetching market data..."):
        summary = analyzer.get_market_summary(condition_id)

    if not summary:
        console.print(f"[red]Market not found: {condition_id}[/red]")
        return

    market = summary['market']

    # Market info panel
    info = f"""
[bold]Question:[/bold] {market['question']}

[bold]Condition ID:[/bold] {market['condition_id']}
[bold]Market Slug:[/bold] {market.get('market_slug', 'N/A')}
[bold]End Date:[/bold] {market.get('end_date_iso', 'N/A')}
[bold]Status:[/bold] {'Active' if market['active'] else 'Inactive'} | {'Closed' if market['closed'] else 'Open'}
"""

    console.print(Panel(info, title="Market Details", border_style="blue"))

    # Tokens/outcomes table
    table = Table(title="Outcomes & Prices", show_header=True, header_style="bold magenta")
    table.add_column("Outcome", style="cyan")
    table.add_column("Current Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Last Updated", justify="right")

    for token in summary['tokens']:
        change = token['change']

        if change:
            if change.change_percent > 0:
                change_str = f"[green]+{change.change_percent:.2f}%[/green]"
            else:
                change_str = f"[red]{change.change_percent:.2f}%[/red]"
        else:
            change_str = "[dim]N/A[/dim]"

        price_str = f"{token['current_price']:.4f}" if token['current_price'] else "[dim]N/A[/dim]"

        timestamp = token['timestamp']
        if timestamp:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime('%Y-%m-%d %H:%M')
        else:
            time_str = "[dim]N/A[/dim]"

        table.add_row(
            token['outcome'],
            price_str,
            change_str,
            time_str
        )

    console.print(table)


@cli.command()
def stats():
    """Show database statistics"""
    db = Database()
    stats = db.get_stats()

    table = Table(title="Database Statistics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Total Markets", str(stats['total_markets']))
    table.add_row("Active Markets", str(stats['active_markets']))
    table.add_row("Total Tokens", str(stats['total_tokens']))
    table.add_row("Price Data Points", str(stats['total_price_points']))

    console.print()
    console.print(table)
    console.print()


@cli.command()
def config_info():
    """Show current configuration"""
    info = f"""
[bold]Configuration[/bold]

[cyan]Database:[/cyan]
  Path: {Config.get_db_path()}

[cyan]Scanner:[/cyan]
  Scan Interval: {Config.SCAN_INTERVAL_SECONDS}s
  Default Change Threshold: {Config.DEFAULT_CHANGE_THRESHOLD}%
  Time Window: {Config.TIME_WINDOW_MINUTES} minutes

[cyan]API:[/cyan]
  CLOB URL: {Config.CLOB_API_URL}
  Chain ID: {Config.CHAIN_ID}
"""

    console.print(Panel(info, title="Configuration", border_style="blue"))


if __name__ == '__main__':
    cli()
