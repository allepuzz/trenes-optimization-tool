"""
Database management for train price tracking.

This module handles all database operations for storing and retrieving
historical train price data for optimization analysis.
"""

import sqlite3
import logging
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import TrainRoute, PriceData, Station, TrainType


logger = logging.getLogger(__name__)


class PriceDatabase:
    """
    SQLite database for storing train price history.

    This class manages the creation, insertion, and querying of historical
    train price data used for optimization algorithms.
    """

    def __init__(self, db_path: str = "train_prices.db"):
        """
        Initialize the price database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self) -> None:
        """
        Create database tables if they don't exist.

        Creates the following tables:
        - stations: Store train station information
        - routes: Store train route definitions
        - prices: Store historical price data
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create stations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create routes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin_id INTEGER NOT NULL,
                    destination_id INTEGER NOT NULL,
                    train_number TEXT NOT NULL,
                    train_type TEXT NOT NULL,
                    departure_time TIMESTAMP NOT NULL,
                    arrival_time TIMESTAMP NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (origin_id) REFERENCES stations (id),
                    FOREIGN KEY (destination_id) REFERENCES stations (id),
                    UNIQUE(origin_id, destination_id, train_number, departure_time)
                )
            """)

            # Create prices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    route_id INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    currency TEXT DEFAULT 'EUR',
                    ticket_type TEXT NOT NULL,
                    availability INTEGER NOT NULL,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    travel_date DATE NOT NULL,
                    FOREIGN KEY (route_id) REFERENCES routes (id)
                )
            """)

            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prices_route_date
                ON prices (route_id, travel_date)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prices_scraped_at
                ON prices (scraped_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_routes_origin_dest
                ON routes (origin_id, destination_id)
            """)

            conn.commit()
            logger.info("Database initialized successfully")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Ensures proper connection handling and automatic cleanup.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()

    def add_station(self, station: Station) -> int:
        """
        Add a station to the database or get existing ID.

        Args:
            station: Station object to add

        Returns:
            int: Station ID in database
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Try to get existing station
            cursor.execute(
                "SELECT id FROM stations WHERE code = ?",
                (station.code,)
            )
            existing = cursor.fetchone()

            if existing:
                return existing['id']

            # Insert new station
            cursor.execute("""
                INSERT INTO stations (code, name, city)
                VALUES (?, ?, ?)
            """, (station.code, station.name, station.city))

            station_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added station: {station.name} (ID: {station_id})")
            return station_id

    def add_route(self, route: TrainRoute) -> int:
        """
        Add a route to the database or get existing ID.

        Args:
            route: TrainRoute object to add

        Returns:
            int: Route ID in database
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Add stations first
            origin_id = self.add_station(route.origin)
            destination_id = self.add_station(route.destination)

            # Try to get existing route
            cursor.execute("""
                SELECT id FROM routes
                WHERE origin_id = ? AND destination_id = ?
                AND train_number = ? AND departure_time = ?
            """, (origin_id, destination_id, route.train_number, route.departure_time))

            existing = cursor.fetchone()
            if existing:
                return existing['id']

            # Insert new route
            cursor.execute("""
                INSERT INTO routes (
                    origin_id, destination_id, train_number, train_type,
                    departure_time, arrival_time, duration_minutes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                origin_id, destination_id, route.train_number, route.train_type.value,
                route.departure_time, route.arrival_time, route.duration_minutes
            ))

            route_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added route: {route.train_number} (ID: {route_id})")
            return route_id

    def add_price_data(self, price_data: PriceData) -> int:
        """
        Add price data to the database.

        Args:
            price_data: PriceData object to store

        Returns:
            int: Price record ID in database
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Add route first
            route_id = self.add_route(price_data.route)

            # Insert price data
            cursor.execute("""
                INSERT INTO prices (
                    route_id, price, currency, ticket_type,
                    availability, scraped_at, travel_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                route_id,
                float(price_data.price),
                price_data.currency,
                price_data.ticket_type,
                price_data.availability,
                price_data.scraped_at,
                price_data.route.departure_time.date()
            ))

            price_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added price data: €{price_data.price} for route {route_id}")
            return price_id

    def get_price_history(
        self,
        origin_code: str,
        destination_code: str,
        travel_date: date,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a specific route.

        Args:
            origin_code: Origin station code
            destination_code: Destination station code
            travel_date: Travel date
            days_back: Number of days of history to retrieve

        Returns:
            List of price records with route information
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    p.price, p.currency, p.ticket_type, p.availability,
                    p.scraped_at, p.travel_date,
                    r.train_number, r.train_type, r.departure_time, r.arrival_time,
                    so.code as origin_code, so.name as origin_name,
                    sd.code as dest_code, sd.name as dest_name
                FROM prices p
                JOIN routes r ON p.route_id = r.id
                JOIN stations so ON r.origin_id = so.id
                JOIN stations sd ON r.destination_id = sd.id
                WHERE so.code = ? AND sd.code = ?
                AND p.travel_date = ?
                AND p.scraped_at >= datetime('now', '-{} days')
                ORDER BY p.scraped_at DESC
            """.format(days_back), (origin_code, destination_code, travel_date))

            results = []
            for row in cursor.fetchall():
                results.append(dict(row))

            logger.info(f"Retrieved {len(results)} price records for {origin_code}-{destination_code}")
            return results

    def get_route_statistics(
        self,
        origin_code: str,
        destination_code: str,
        travel_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get statistical analysis of prices for a route.

        Args:
            origin_code: Origin station code
            destination_code: Destination station code
            travel_date: Travel date

        Returns:
            Dictionary with price statistics or None if no data
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as data_points,
                    MIN(p.price) as min_price,
                    MAX(p.price) as max_price,
                    AVG(p.price) as avg_price,
                    MIN(p.scraped_at) as first_seen,
                    MAX(p.scraped_at) as last_seen
                FROM prices p
                JOIN routes r ON p.route_id = r.id
                JOIN stations so ON r.origin_id = so.id
                JOIN stations sd ON r.destination_id = sd.id
                WHERE so.code = ? AND sd.code = ? AND p.travel_date = ?
            """, (origin_code, destination_code, travel_date))

            result = cursor.fetchone()

            if result and result['data_points'] > 0:
                stats = dict(result)
                stats['price_range'] = stats['max_price'] - stats['min_price']
                return stats

            return None

    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """
        Remove old price data to keep database size manageable.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            Number of records deleted
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM prices
                WHERE scraped_at < datetime('now', '-{} days')
            """.format(days_to_keep))

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Cleaned up {deleted_count} old price records")
            return deleted_count

    def get_database_stats(self) -> Dict[str, int]:
        """
        Get overall database statistics.

        Returns:
            Dictionary with counts of stations, routes, and prices
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) as count FROM stations")
            stats['stations'] = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM routes")
            stats['routes'] = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM prices")
            stats['prices'] = cursor.fetchone()['count']

            cursor.execute("""
                SELECT COUNT(DISTINCT travel_date) as count FROM prices
            """)
            stats['unique_travel_dates'] = cursor.fetchone()['count']

            return stats