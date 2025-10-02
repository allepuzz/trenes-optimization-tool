"""
Trenes Tool - Spanish train ticket optimization core library.

This module provides the core functionality for scraping and optimizing
Spanish train ticket purchases.
"""

__version__ = "0.1.0"
__author__ = "Angel"
__email__ = "your-email@example.com"

from .scraper import RenfeScraper
from .optimizer import PriceOptimizer
from .models import TrainRoute, PriceData, OptimizationResult

__all__ = [
    "RenfeScraper",
    "PriceOptimizer",
    "TrainRoute",
    "PriceData",
    "OptimizationResult",
]