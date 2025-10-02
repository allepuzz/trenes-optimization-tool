"""
Test script for Murcia-Madrid route scraping.

This script tests the web scraping functionality with real Renfe data
and stores results in the database for analysis.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import our modules
import sys
sys.path.insert(0, 'src')

from trenes_tool.scraper import RenfeScraper
from trenes_tool.database import PriceDatabase
from trenes_tool.models import Station, TrainRoute, PriceData, TrainType


async def test_murcia_madrid_scraping():
    """
    Test scraping Murcia to Madrid train routes.

    This function demonstrates the complete workflow:
    1. Initialize scraper and database
    2. Search for train routes
    3. Extract price information
    4. Store data in database
    5. Retrieve and analyze historical data
    """
    print("Testing Murcia-Madrid train scraping...")

    # Initialize database
    db = PriceDatabase("test_prices.db")
    print("Database initialized")

    # Test date (tomorrow for realistic results)
    test_date = date.today() + timedelta(days=7)
    print(f"Testing date: {test_date}")

    try:
        # Initialize scraper (non-headless for debugging)
        async with RenfeScraper(headless=False, timeout=45000) as scraper:
            print("Browser started, navigating to Renfe...")

            # Navigate to Renfe homepage
            await scraper.page.goto(scraper.SEARCH_URL, timeout=60000)
            print("Renfe page loaded")

            # Take a screenshot for debugging
            await scraper.page.screenshot(path="renfe_homepage.png")
            print("Screenshot saved: renfe_homepage.png")

            # Get page title to confirm we're on the right page
            title = await scraper.page.title()
            print(f"Page title: {title}")

            # Get all input fields to understand the form structure
            print("Analyzing form structure...")
            inputs = await scraper.page.query_selector_all("input")

            input_info = []
            for i, input_elem in enumerate(inputs):
                input_type = await input_elem.get_attribute("type")
                input_name = await input_elem.get_attribute("name")
                input_id = await input_elem.get_attribute("id")
                input_placeholder = await input_elem.get_attribute("placeholder")

                input_info.append({
                    "index": i,
                    "type": input_type,
                    "name": input_name,
                    "id": input_id,
                    "placeholder": input_placeholder
                })

            print(f"Found {len(input_info)} input fields:")
            for info in input_info[:10]:  # Show first 10
                print(f"  - Type: {info['type']}, Name: {info['name']}, ID: {info['id']}, Placeholder: {info['placeholder']}")

            # Look for buttons
            buttons = await scraper.page.query_selector_all("button")
            print(f"Found {len(buttons)} buttons:")

            for i, button in enumerate(buttons[:5]):  # Show first 5
                button_text = await button.text_content()
                button_type = await button.get_attribute("type")
                print(f"  - Button {i}: '{button_text}' (type: {button_type})")

            # Try to fill the search form
            print("Attempting to fill search form...")
            try:
                await scraper._fill_search_form("Murcia", "Madrid", test_date)
                print("Form filled successfully")

                # Take another screenshot
                await scraper.page.screenshot(path="form_filled.png")
                print("Screenshot saved: form_filled.png")

                # Try to submit the search
                print("Submitting search...")
                await scraper._submit_search()

                # Wait for results page
                await scraper.page.wait_for_timeout(5000)

                # Take screenshot of results
                await scraper.page.screenshot(path="search_results.png")
                print("Results screenshot saved: search_results.png")

                # Get page content for analysis
                content = await scraper.page.content()
                print(f"Page content length: {len(content)} characters")

                # Look for train-related elements
                train_elements = await scraper.page.query_selector_all("[class*='tren'], [class*='train'], [class*='viaje']")
                print(f"Found {len(train_elements)} potential train elements")

            except Exception as e:
                print(f"Error during form interaction: {e}")

                # Still take a screenshot for debugging
                await scraper.page.screenshot(path="error_state.png")
                print("Error screenshot saved: error_state.png")

    except Exception as e:
        print(f"Scraping failed: {e}")

    # Test database functionality with dummy data
    print("\nTesting database functionality...")

    # Create test stations
    murcia_station = Station(code="MURCI", name="Murcia", city="Murcia")
    madrid_station = Station(code="MADRI", name="Madrid-Puerta de Atocha", city="Madrid")

    # Create test route
    test_route = TrainRoute(
        origin=murcia_station,
        destination=madrid_station,
        departure_time=datetime.combine(test_date, datetime.min.time().replace(hour=8, minute=30)),
        arrival_time=datetime.combine(test_date, datetime.min.time().replace(hour=12, minute=15)),
        train_type=TrainType.AVE,
        train_number="AVE02104",
        duration_minutes=225
    )

    # Create test price data
    test_price = PriceData(
        route=test_route,
        price=Decimal("45.50"),
        ticket_type="Turista",
        availability=87
    )

    # Store in database
    price_id = db.add_price_data(test_price)
    print(f"Test price data stored with ID: {price_id}")

    # Get database statistics
    stats = db.get_database_stats()
    print("Database statistics:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # Test price history retrieval
    history = db.get_price_history("MURCI", "MADRI", test_date)
    print(f"Retrieved {len(history)} historical price records")

    if history:
        latest = history[0]
        print(f"Latest price: €{latest['price']} ({latest['ticket_type']})")

    print("\nTest completed! Check the screenshots and database for results.")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_murcia_madrid_scraping())