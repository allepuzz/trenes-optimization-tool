"""
Web scraper for Spanish train ticket prices.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import requests

from .models import TrainRoute, PriceData, Station, TrainType


logger = logging.getLogger(__name__)


class RenfeScraper:
    """Web scraper for Renfe train tickets."""

    BASE_URL = "https://www.renfe.com"
    SEARCH_URL = "https://www.renfe.com/es/"

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize the scraper.

        Args:
            headless: Run browser in headless mode
            timeout: Page timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Start the browser and create a new page."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()

        # Set user agent to avoid detection
        await self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    async def close(self) -> None:
        """Close the browser."""
        if self.browser:
            await self.browser.close()

    async def search_routes(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None
    ) -> List[TrainRoute]:
        """
        Search for available train routes.

        Args:
            origin: Origin station name or code
            destination: Destination station name or code
            departure_date: Date of departure
            return_date: Optional return date for round trip

        Returns:
            List of available train routes
        """
        if not self.page:
            raise RuntimeError("Scraper not started. Use async with or call start() first.")

        try:
            # Navigate to search page
            await self.page.goto(self.SEARCH_URL, timeout=self.timeout)

            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")

            # Fill search form
            await self._fill_search_form(origin, destination, departure_date, return_date)

            # Submit search
            await self._submit_search()

            # Wait for results
            await self.page.wait_for_selector("[data-testid='train-result']", timeout=self.timeout)

            # Parse results
            routes = await self._parse_search_results()

            return routes

        except Exception as e:
            logger.error(f"Error searching routes: {e}")
            raise

    async def get_price_details(
        self,
        route: TrainRoute,
        ticket_types: Optional[List[str]] = None
    ) -> List[PriceData]:
        """
        Get detailed price information for a specific route.

        Args:
            route: Train route to get prices for
            ticket_types: Specific ticket types to check

        Returns:
            List of price data for different ticket types
        """
        if not self.page:
            raise RuntimeError("Scraper not started.")

        try:
            # Click on the specific route to get details
            route_selector = f"[data-train-number='{route.train_number}']"
            await self.page.click(route_selector)

            # Wait for price details to load
            await self.page.wait_for_selector(".price-selector", timeout=self.timeout)

            # Parse price information
            prices = await self._parse_price_details(route)

            return prices

        except Exception as e:
            logger.error(f"Error getting price details: {e}")
            return []

    async def _fill_search_form(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None
    ) -> None:
        """Fill the search form with travel details."""
        try:
            # Wait for the page to load completely
            await self.page.wait_for_load_state("networkidle")

            # Try multiple common selector patterns for train booking sites
            origin_selectors = [
                "#origen",
                "#origin",
                "input[name='origen']",
                "input[name='origin']",
                "[placeholder*='Origen']",
                "[placeholder*='Origin']",
                "input[type='text']:first-child"
            ]

            # Fill origin
            origin_filled = False
            for selector in origin_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=2000)
                    await self.page.fill(selector, origin)
                    await self.page.wait_for_timeout(1000)
                    origin_filled = True
                    logger.info(f"Origin filled using selector: {selector}")
                    break
                except:
                    continue

            if not origin_filled:
                logger.warning("Could not find origin input field")

            # Fill destination
            destination_selectors = [
                "#destino",
                "#destination",
                "input[name='destino']",
                "input[name='destination']",
                "[placeholder*='Destino']",
                "[placeholder*='Destination']",
                "input[type='text']:nth-child(2)"
            ]

            destination_filled = False
            for selector in destination_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=2000)
                    await self.page.fill(selector, destination)
                    await self.page.wait_for_timeout(1000)
                    destination_filled = True
                    logger.info(f"Destination filled using selector: {selector}")
                    break
                except:
                    continue

            if not destination_filled:
                logger.warning("Could not find destination input field")

            # Fill departure date
            date_selectors = [
                "#fecha_ida",
                "#departure_date",
                "input[name='fecha_ida']",
                "input[name='departure']",
                "input[type='date']",
                "[placeholder*='fecha']",
                "[placeholder*='date']"
            ]

            date_str = departure_date.strftime("%d/%m/%Y")
            date_filled = False

            for selector in date_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=2000)

                    # Try different date formats
                    date_formats = [
                        departure_date.strftime("%d/%m/%Y"),
                        departure_date.strftime("%Y-%m-%d"),
                        departure_date.strftime("%m/%d/%Y")
                    ]

                    for date_format in date_formats:
                        try:
                            await self.page.fill(selector, date_format)
                            date_filled = True
                            logger.info(f"Date filled using selector: {selector} with format: {date_format}")
                            break
                        except:
                            continue

                    if date_filled:
                        break

                except:
                    continue

            if not date_filled:
                logger.warning("Could not find date input field")

        except Exception as e:
            logger.error(f"Error filling search form: {e}")
            raise

    async def _submit_search(self) -> None:
        """Submit the search form."""
        # Try multiple common search button selectors
        search_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "#buscar",
            "#search",
            ".btn-search",
            ".search-btn",
            "[data-testid='search-button']",
            "button:has-text('Buscar')",
            "button:has-text('Search')",
            "button:has-text('Consultar')"
        ]

        search_clicked = False
        for selector in search_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=2000)
                await self.page.click(selector)
                search_clicked = True
                logger.info(f"Search submitted using selector: {selector}")
                break
            except:
                continue

        if not search_clicked:
            logger.warning("Could not find search button")
            # Try pressing Enter on the last filled field as fallback
            await self.page.keyboard.press("Enter")

    async def _parse_search_results(self) -> List[TrainRoute]:
        """Parse search results from the page."""
        # Get page content
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')

        routes = []

        # Find all train result elements
        train_results = soup.find_all("[data-testid='train-result']")

        for result in train_results:
            try:
                route = self._extract_route_from_element(result)
                if route:
                    routes.append(route)
            except Exception as e:
                logger.warning(f"Error parsing route element: {e}")
                continue

        return routes

    def _extract_route_from_element(self, element) -> Optional[TrainRoute]:
        """Extract route information from a DOM element."""
        # This is a placeholder implementation
        # In reality, you'd need to inspect the actual Renfe website structure
        # and adapt the selectors accordingly

        try:
            # Extract basic information (adapt selectors to actual website)
            train_number = element.get("data-train-number", "")
            departure_time_str = element.find(".departure-time").text.strip()
            arrival_time_str = element.find(".arrival-time").text.strip()

            # Parse times (this would need adjustment based on actual format)
            departure_time = datetime.strptime(departure_time_str, "%H:%M")
            arrival_time = datetime.strptime(arrival_time_str, "%H:%M")

            # Create route object (with placeholder data)
            route = TrainRoute(
                origin=Station(code="ORIG", name="Origin", city="Origin City"),
                destination=Station(code="DEST", name="Destination", city="Destination City"),
                departure_time=departure_time,
                arrival_time=arrival_time,
                train_type=TrainType.AVE,  # Would need to extract from actual data
                train_number=train_number,
                duration_minutes=120  # Calculate from times
            )

            return route

        except Exception as e:
            logger.error(f"Error extracting route data: {e}")
            return None

    async def _parse_price_details(self, route: TrainRoute) -> List[PriceData]:
        """Parse price details for a specific route."""
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')

        prices = []

        # Find price elements (adapt to actual website structure)
        price_elements = soup.find_all(".price-option")

        for element in price_elements:
            try:
                price_data = self._extract_price_from_element(element, route)
                if price_data:
                    prices.append(price_data)
            except Exception as e:
                logger.warning(f"Error parsing price element: {e}")
                continue

        return prices

    def _extract_price_from_element(self, element, route: TrainRoute) -> Optional[PriceData]:
        """Extract price information from a DOM element."""
        # Placeholder implementation - adapt to actual website structure
        try:
            price_text = element.find(".price").text.strip()
            price_value = float(price_text.replace("€", "").replace(",", "."))

            ticket_type = element.find(".ticket-type").text.strip()
            availability = int(element.get("data-availability", "0"))

            price_data = PriceData(
                route=route,
                price=price_value,
                ticket_type=ticket_type,
                availability=availability
            )

            return price_data

        except Exception as e:
            logger.error(f"Error extracting price data: {e}")
            return None


# Utility function for quick searches
async def quick_search(
    origin: str,
    destination: str,
    departure_date: date,
    headless: bool = True
) -> List[TrainRoute]:
    """
    Quick search function for train routes.

    Args:
        origin: Origin station
        destination: Destination station
        departure_date: Date of travel
        headless: Run browser in headless mode

    Returns:
        List of available routes
    """
    async with RenfeScraper(headless=headless) as scraper:
        return await scraper.search_routes(origin, destination, departure_date)