"""
Command-line interface for the Trenes optimization tool.
"""

import asyncio
from datetime import date, datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import quick_search, RenfeScraper
from .optimizer import PriceOptimizer
from .models import TrainRoute


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    Trenes Optimization Tool - Spanish train ticket price optimizer.

    Find the best time to buy Spanish train tickets using web scraping
    and historical price analysis.
    """
    pass


@main.command()
@click.option("--origin", "-o", required=True, help="Origin station (e.g., 'Madrid')")
@click.option("--destination", "-d", required=True, help="Destination station (e.g., 'Barcelona')")
@click.option("--date", "-dt", required=True, help="Travel date (YYYY-MM-DD)")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
def search(origin: str, destination: str, date: str, headless: bool):
    """Search for available train routes."""
    try:
        travel_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        console.print("❌ Invalid date format. Use YYYY-MM-DD", style="red")
        return

    with console.status("[bold green]Searching for trains..."):
        try:
            routes = asyncio.run(quick_search(origin, destination, travel_date, headless))

            if not routes:
                console.print("❌ No routes found", style="red")
                return

            # Display results in a table
            table = Table(title=f"Train Routes: {origin} → {destination} ({date})")
            table.add_column("Train", style="cyan", no_wrap=True)
            table.add_column("Departure", style="green")
            table.add_column("Arrival", style="green")
            table.add_column("Duration", style="yellow")
            table.add_column("Type", style="magenta")

            for route in routes:
                duration_hours = route.duration_minutes // 60
                duration_mins = route.duration_minutes % 60
                duration_str = f"{duration_hours}h {duration_mins}m"

                table.add_row(
                    route.train_number,
                    route.departure_time.strftime("%H:%M"),
                    route.arrival_time.strftime("%H:%M"),
                    duration_str,
                    route.train_type.value
                )

            console.print(table)

        except Exception as e:
            console.print(f"❌ Error searching for routes: {e}", style="red")


@main.command()
@click.option("--origin", "-o", required=True, help="Origin station")
@click.option("--destination", "-d", required=True, help="Destination station")
@click.option("--date", "-dt", required=True, help="Travel date (YYYY-MM-DD)")
@click.option("--train", "-t", help="Specific train number")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
def prices(origin: str, destination: str, date: str, train: Optional[str], headless: bool):
    """Get detailed price information for routes."""
    try:
        travel_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        console.print("❌ Invalid date format. Use YYYY-MM-DD", style="red")
        return

    with console.status("[bold green]Getting price information..."):
        try:
            # First search for routes
            routes = asyncio.run(quick_search(origin, destination, travel_date, headless))

            if not routes:
                console.print("❌ No routes found", style="red")
                return

            # Filter by train number if specified
            if train:
                routes = [r for r in routes if r.train_number == train]
                if not routes:
                    console.print(f"❌ Train {train} not found", style="red")
                    return

            # Get price details for each route
            async def get_all_prices():
                async with RenfeScraper(headless=headless) as scraper:
                    all_prices = []
                    for route in routes:
                        prices_data = await scraper.get_price_details(route)
                        all_prices.extend(prices_data)
                    return all_prices

            prices_data = asyncio.run(get_all_prices())

            if not prices_data:
                console.print("❌ No price data found", style="red")
                return

            # Display price information
            table = Table(title=f"Price Information: {origin} → {destination} ({date})")
            table.add_column("Train", style="cyan")
            table.add_column("Departure", style="green")
            table.add_column("Ticket Type", style="yellow")
            table.add_column("Price", style="bold green")
            table.add_column("Availability", style="blue")

            for price_data in prices_data:
                table.add_row(
                    price_data.route.train_number,
                    price_data.route.departure_time.strftime("%H:%M"),
                    price_data.ticket_type,
                    f"€{price_data.price}",
                    str(price_data.availability)
                )

            console.print(table)

        except Exception as e:
            console.print(f"❌ Error getting prices: {e}", style="red")


@main.command()
@click.option("--origin", "-o", required=True, help="Origin station")
@click.option("--destination", "-d", required=True, help="Destination station")
@click.option("--date", "-dt", required=True, help="Travel date (YYYY-MM-DD)")
@click.option("--price", "-p", type=float, required=True, help="Current price in euros")
def optimize(origin: str, destination: str, date: str, price: float):
    """Get optimization recommendation for a ticket price."""
    try:
        travel_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        console.print("❌ Invalid date format. Use YYYY-MM-DD", style="red")
        return

    # Create a dummy route for optimization (in real usage, this would come from scraping)
    from .models import Station, TrainType
    dummy_route = TrainRoute(
        origin=Station(code="ORIG", name=origin, city=origin),
        destination=Station(code="DEST", name=destination, city=destination),
        departure_time=datetime.combine(travel_date, datetime.min.time()),
        arrival_time=datetime.combine(travel_date, datetime.min.time()),
        train_type=TrainType.AVE,
        train_number="DEMO",
        duration_minutes=120
    )

    optimizer = PriceOptimizer()
    result = optimizer.get_optimization_recommendation(dummy_route, price)

    # Display recommendation
    color = {
        "BUY_NOW": "green",
        "WAIT": "yellow",
        "PRICE_ALERT": "cyan",
        "NO_DATA": "red"
    }.get(result.recommendation.value, "white")

    panel = Panel(
        f"""[bold]Recommendation:[/bold] [{color}]{result.recommendation.value}[/{color}]
[bold]Confidence:[/bold] {result.confidence:.1%}
[bold]Reasoning:[/bold] {result.reasoning}
[bold]Suggested Action:[/bold] {result.suggested_action}

[bold]Details:[/bold]
• Days until departure: {result.days_until_departure}
• Price trend: {result.price_trend or 'Unknown'}
• Optimal window: {result.optimal_purchase_window or 'Unknown'}""",
        title=f"Price Optimization: €{price}",
        expand=False
    )

    console.print(panel)


@main.command()
def demo():
    """Run a demo of the optimization tool."""
    console.print(Panel(
        """[bold green]Trenes Optimization Tool Demo[/bold green]

This tool helps you find the best time to buy Spanish train tickets by:

1. [bold]Scraping[/bold] current prices from train websites
2. [bold]Analyzing[/bold] historical price patterns
3. [bold]Recommending[/bold] optimal purchase timing
4. [bold]Agent Integration[/bold] via LangGraph
5. [bold]MCP Server[/bold] for Claude Code integration

[bold]Example Commands:[/bold]

Search for routes:
[cyan]trenes-tool search -o "Madrid" -d "Barcelona" --date 2024-12-25[/cyan]

Get price information:
[cyan]trenes-tool prices -o "Madrid" -d "Barcelona" --date 2024-12-25[/cyan]

Get optimization recommendation:
[cyan]trenes-tool optimize -o "Madrid" -d "Barcelona" --date 2024-12-25 --price 45.50[/cyan]

[bold yellow]Note:[/bold yellow] This is a learning project. Web scraping functionality
requires adaptation to actual train booking websites.""",
        title="Welcome to Trenes Tool",
        expand=False
    ))


if __name__ == "__main__":
    main()