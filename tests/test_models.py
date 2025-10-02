"""
Test cases for data models.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from trenes_tool.models import (
    Station,
    TrainRoute,
    PriceData,
    TrainType,
    OptimizationRecommendation,
    OptimizationResult
)


def test_station_creation():
    """Test Station model creation."""
    station = Station(
        code="MADRI",
        name="Madrid-Puerta de Atocha",
        city="Madrid"
    )

    assert station.code == "MADRI"
    assert station.name == "Madrid-Puerta de Atocha"
    assert station.city == "Madrid"


def test_train_route_creation():
    """Test TrainRoute model creation."""
    origin = Station(code="MADRI", name="Madrid-Atocha", city="Madrid")
    destination = Station(code="BCNSA", name="Barcelona-Sants", city="Barcelona")

    departure = datetime(2024, 12, 25, 8, 0)
    arrival = datetime(2024, 12, 25, 10, 30)

    route = TrainRoute(
        origin=origin,
        destination=destination,
        departure_time=departure,
        arrival_time=arrival,
        train_type=TrainType.AVE,
        train_number="AVE2104",
        duration_minutes=150
    )

    assert route.origin.code == "MADRI"
    assert route.destination.code == "BCNSA"
    assert route.train_type == TrainType.AVE
    assert route.duration_minutes == 150


def test_price_data_creation():
    """Test PriceData model creation."""
    origin = Station(code="MADRI", name="Madrid-Atocha", city="Madrid")
    destination = Station(code="BCNSA", name="Barcelona-Sants", city="Barcelona")

    route = TrainRoute(
        origin=origin,
        destination=destination,
        departure_time=datetime(2024, 12, 25, 8, 0),
        arrival_time=datetime(2024, 12, 25, 10, 30),
        train_type=TrainType.AVE,
        train_number="AVE2104",
        duration_minutes=150
    )

    price_data = PriceData(
        route=route,
        price=Decimal("45.50"),
        ticket_type="Turista",
        availability=50
    )

    assert price_data.price == Decimal("45.50")
    assert price_data.currency == "EUR"
    assert price_data.ticket_type == "Turista"
    assert price_data.availability == 50


def test_optimization_result_creation():
    """Test OptimizationResult model creation."""
    result = OptimizationResult(
        route_key="MADRI_BCNSA_2024-12-25_AVE",
        current_price=Decimal("45.50"),
        recommendation=OptimizationRecommendation.BUY_NOW,
        confidence=0.85,
        reasoning="Price is near historical low",
        suggested_action="Book your ticket immediately",
        days_until_departure=7
    )

    assert result.recommendation == OptimizationRecommendation.BUY_NOW
    assert result.confidence == 0.85
    assert result.days_until_departure == 7


def test_train_type_enum():
    """Test TrainType enum values."""
    assert TrainType.AVE == "AVE"
    assert TrainType.AVLO == "AVLO"
    assert TrainType.REGIONAL == "REGIONAL"


def test_optimization_recommendation_enum():
    """Test OptimizationRecommendation enum values."""
    assert OptimizationRecommendation.BUY_NOW == "BUY_NOW"
    assert OptimizationRecommendation.WAIT == "WAIT"
    assert OptimizationRecommendation.PRICE_ALERT == "PRICE_ALERT"
    assert OptimizationRecommendation.NO_DATA == "NO_DATA"