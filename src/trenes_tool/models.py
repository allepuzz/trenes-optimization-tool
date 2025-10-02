"""
Data models for the trenes optimization tool.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TrainType(str, Enum):
    """Types of Spanish trains."""
    AVE = "AVE"
    AVLO = "AVLO"
    ALVIA = "ALVIA"
    ALTARIA = "ALTARIA"
    TALGO = "TALGO"
    INTERCITY = "INTERCITY"
    REGIONAL = "REGIONAL"
    CERCANIAS = "CERCANIAS"


class Station(BaseModel):
    """Train station model."""
    code: str = Field(..., description="Station code (e.g., 'MADRI')")
    name: str = Field(..., description="Station name (e.g., 'Madrid-Puerta de Atocha')")
    city: str = Field(..., description="City name")


class TrainRoute(BaseModel):
    """Train route information."""
    origin: Station
    destination: Station
    departure_time: datetime
    arrival_time: datetime
    train_type: TrainType
    train_number: str
    duration_minutes: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PriceData(BaseModel):
    """Price information for a train route."""
    route: TrainRoute
    price: Decimal = Field(..., description="Price in euros")
    currency: str = Field(default="EUR")
    ticket_type: str = Field(..., description="Ticket type (e.g., 'Turista', 'Preferente')")
    availability: int = Field(..., description="Number of seats available")
    scraped_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class PriceHistory(BaseModel):
    """Historical price data for analysis."""
    route_key: str = Field(..., description="Unique identifier for route+date combination")
    prices: List[PriceData] = Field(default_factory=list)
    lowest_price: Optional[Decimal] = None
    highest_price: Optional[Decimal] = None
    average_price: Optional[Decimal] = None

    def add_price(self, price_data: PriceData) -> None:
        """Add new price data point."""
        self.prices.append(price_data)
        self._update_statistics()

    def _update_statistics(self) -> None:
        """Update price statistics."""
        if not self.prices:
            return

        prices = [p.price for p in self.prices]
        self.lowest_price = min(prices)
        self.highest_price = max(prices)
        self.average_price = sum(prices) / len(prices)


class OptimizationRecommendation(str, Enum):
    """Optimization recommendations."""
    BUY_NOW = "BUY_NOW"
    WAIT = "WAIT"
    PRICE_ALERT = "PRICE_ALERT"
    NO_DATA = "NO_DATA"


class OptimizationResult(BaseModel):
    """Result of price optimization analysis."""
    route_key: str
    current_price: Decimal
    recommendation: OptimizationRecommendation
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in recommendation (0-1)")
    reasoning: str = Field(..., description="Human-readable explanation")
    suggested_action: str = Field(..., description="Specific action to take")
    price_trend: Optional[str] = None  # "rising", "falling", "stable"
    optimal_purchase_window: Optional[str] = None  # e.g., "2-3 days before departure"

    # Additional insights
    days_until_departure: int
    historical_low: Optional[Decimal] = None
    historical_high: Optional[Decimal] = None
    price_volatility: Optional[float] = None