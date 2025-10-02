"""
Price optimization engine for Spanish train tickets.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from statistics import mean, stdev

from .models import (
    PriceData,
    PriceHistory,
    OptimizationResult,
    OptimizationRecommendation,
    TrainRoute
)


logger = logging.getLogger(__name__)


class PriceOptimizer:
    """
    Price optimization engine that analyzes historical data
    and provides purchase timing recommendations.
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize the optimizer.

        Args:
            confidence_threshold: Minimum confidence level for recommendations
        """
        self.confidence_threshold = confidence_threshold
        self.price_histories: Dict[str, PriceHistory] = {}

    def add_price_data(self, price_data: PriceData) -> None:
        """
        Add new price data to the optimization engine.

        Args:
            price_data: New price data point
        """
        route_key = self._generate_route_key(price_data.route, price_data.route.departure_time.date())

        if route_key not in self.price_histories:
            self.price_histories[route_key] = PriceHistory(route_key=route_key)

        self.price_histories[route_key].add_price(price_data)

    def get_optimization_recommendation(
        self,
        route: TrainRoute,
        current_price: Decimal,
        travel_date: Optional[datetime] = None
    ) -> OptimizationResult:
        """
        Get optimization recommendation for a specific route and price.

        Args:
            route: Train route
            current_price: Current price for the route
            travel_date: Travel date (defaults to route departure time)

        Returns:
            Optimization result with recommendation and reasoning
        """
        if travel_date is None:
            travel_date = route.departure_time

        route_key = self._generate_route_key(route, travel_date.date())
        days_until_departure = (travel_date.date() - datetime.now().date()).days

        # Get historical data
        history = self.price_histories.get(route_key)

        if not history or len(history.prices) < 3:
            return self._no_data_recommendation(route_key, current_price, days_until_departure)

        # Analyze price trends
        analysis = self._analyze_price_trends(history, current_price)

        # Generate recommendation based on analysis
        recommendation = self._generate_recommendation(
            current_price, days_until_departure, analysis, history
        )

        return recommendation

    def _generate_route_key(self, route: TrainRoute, travel_date) -> str:
        """Generate unique key for route+date combination."""
        return f"{route.origin.code}_{route.destination.code}_{travel_date}_{route.train_type}"

    def _no_data_recommendation(
        self,
        route_key: str,
        current_price: Decimal,
        days_until_departure: int
    ) -> OptimizationResult:
        """Generate recommendation when no historical data is available."""
        # Basic heuristics for when no data is available
        if days_until_departure <= 7:
            recommendation = OptimizationRecommendation.BUY_NOW
            reasoning = "Limited time until departure. Book now to secure your seat."
            confidence = 0.5
        elif days_until_departure <= 30:
            recommendation = OptimizationRecommendation.WAIT
            reasoning = "Monitor prices for a few more days before booking."
            confidence = 0.3
        else:
            recommendation = OptimizationRecommendation.WAIT
            reasoning = "Too early to book. Wait for better price data."
            confidence = 0.4

        return OptimizationResult(
            route_key=route_key,
            current_price=current_price,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            suggested_action=self._get_suggested_action(recommendation),
            days_until_departure=days_until_departure
        )

    def _analyze_price_trends(self, history: PriceHistory, current_price: Decimal) -> Dict[str, Any]:
        """Analyze price trends from historical data."""
        prices = [p.price for p in history.prices]
        recent_prices = [p.price for p in history.prices[-7:]]  # Last 7 data points

        analysis = {
            "historical_low": min(prices),
            "historical_high": max(prices),
            "historical_average": mean(prices),
            "recent_average": mean(recent_prices) if recent_prices else current_price,
            "price_volatility": stdev(prices) if len(prices) > 1 else 0,
            "current_vs_historical_low": float(current_price / min(prices)),
            "current_vs_average": float(current_price / mean(prices)),
            "trend": self._calculate_trend(recent_prices),
            "is_outlier": self._is_price_outlier(current_price, prices)
        }

        return analysis

    def _calculate_trend(self, prices: List[Decimal]) -> str:
        """Calculate recent price trend."""
        if len(prices) < 2:
            return "stable"

        # Simple trend calculation
        recent_change = (prices[-1] - prices[0]) / prices[0]

        if recent_change > 0.05:  # 5% increase
            return "rising"
        elif recent_change < -0.05:  # 5% decrease
            return "falling"
        else:
            return "stable"

    def _is_price_outlier(self, current_price: Decimal, historical_prices: List[Decimal]) -> bool:
        """Determine if current price is an outlier."""
        if len(historical_prices) < 3:
            return False

        avg = mean(historical_prices)
        std = stdev(historical_prices)

        # Price is outlier if it's more than 2 standard deviations from mean
        return abs(current_price - avg) > 2 * std

    def _generate_recommendation(
        self,
        current_price: Decimal,
        days_until_departure: int,
        analysis: Dict[str, Any],
        history: PriceHistory
    ) -> OptimizationResult:
        """Generate optimization recommendation based on analysis."""
        # Initialize variables
        recommendation = OptimizationRecommendation.WAIT
        confidence = 0.5
        reasoning = ""

        # Decision logic based on multiple factors
        factors = []

        # Factor 1: Days until departure
        if days_until_departure <= 3:
            factors.append(("urgent", 0.8, "Very close to departure"))
            recommendation = OptimizationRecommendation.BUY_NOW
        elif days_until_departure <= 7:
            factors.append(("soon", 0.6, "Close to departure"))
        elif days_until_departure <= 14:
            factors.append(("moderate", 0.4, "Moderate time remaining"))
        else:
            factors.append(("early", 0.2, "Plenty of time"))

        # Factor 2: Price vs historical data
        if analysis["current_vs_historical_low"] <= 1.1:  # Within 10% of historical low
            factors.append(("excellent_price", 0.9, "Excellent price"))
            recommendation = OptimizationRecommendation.BUY_NOW
        elif analysis["current_vs_average"] <= 0.9:  # 10% below average
            factors.append(("good_price", 0.7, "Good price"))
        elif analysis["current_vs_average"] >= 1.2:  # 20% above average
            factors.append(("high_price", 0.8, "High price"))
            if days_until_departure > 7:
                recommendation = OptimizationRecommendation.WAIT

        # Factor 3: Price trend
        if analysis["trend"] == "falling":
            factors.append(("falling_trend", 0.6, "Prices are falling"))
            if recommendation != OptimizationRecommendation.BUY_NOW:
                recommendation = OptimizationRecommendation.WAIT
        elif analysis["trend"] == "rising":
            factors.append(("rising_trend", 0.7, "Prices are rising"))
            recommendation = OptimizationRecommendation.BUY_NOW

        # Factor 4: Price volatility
        if analysis["price_volatility"] > analysis["historical_average"] * 0.1:
            factors.append(("volatile", 0.3, "Volatile pricing"))

        # Calculate overall confidence
        confidence = mean([factor[1] for factor in factors])

        # Build reasoning
        reasoning_parts = [factor[2] for factor in factors]
        reasoning = ". ".join(reasoning_parts) + "."

        # Override with price alert if conditions are met
        if (analysis["is_outlier"] and
            analysis["current_vs_historical_low"] <= 1.05 and
            days_until_departure > 1):
            recommendation = OptimizationRecommendation.PRICE_ALERT

        return OptimizationResult(
            route_key=history.route_key,
            current_price=current_price,
            recommendation=recommendation,
            confidence=min(confidence, 1.0),
            reasoning=reasoning,
            suggested_action=self._get_suggested_action(recommendation),
            price_trend=analysis["trend"],
            optimal_purchase_window=self._get_optimal_window(days_until_departure, analysis),
            days_until_departure=days_until_departure,
            historical_low=analysis["historical_low"],
            historical_high=analysis["historical_high"],
            price_volatility=analysis["price_volatility"]
        )

    def _get_suggested_action(self, recommendation: OptimizationRecommendation) -> str:
        """Get human-readable suggested action."""
        actions = {
            OptimizationRecommendation.BUY_NOW: "Book your ticket immediately",
            OptimizationRecommendation.WAIT: "Wait and monitor prices for a few more days",
            OptimizationRecommendation.PRICE_ALERT: "Excellent price! Consider booking if your plans are confirmed",
            OptimizationRecommendation.NO_DATA: "Monitor prices to gather more data"
        }
        return actions.get(recommendation, "Monitor prices")

    def _get_optimal_window(self, days_until_departure: int, analysis: Dict[str, Any]) -> str:
        """Suggest optimal purchase window."""
        if days_until_departure <= 3:
            return "Now - very close to departure"
        elif analysis["trend"] == "falling":
            return "2-4 days before departure"
        elif analysis["price_volatility"] > analysis["historical_average"] * 0.1:
            return "1-2 weeks before departure"
        else:
            return "1-2 weeks before departure"

    def get_price_statistics(self, route_key: str) -> Optional[Dict[str, Any]]:
        """Get price statistics for a specific route."""
        history = self.price_histories.get(route_key)
        if not history:
            return None

        prices = [p.price for p in history.prices]

        return {
            "route_key": route_key,
            "total_data_points": len(prices),
            "lowest_price": min(prices),
            "highest_price": max(prices),
            "average_price": mean(prices),
            "price_volatility": stdev(prices) if len(prices) > 1 else 0,
            "data_collection_period": {
                "start": min(p.scraped_at for p in history.prices),
                "end": max(p.scraped_at for p in history.prices)
            }
        }