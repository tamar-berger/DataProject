"""
Data Cleaner Module for Country Recommendation System

This module provides comprehensive data cleaning, normalization, and validation
for country indicator datasets. It processes CSV files into a standardized
SQLite database suitable for recommendation algorithms.

Main Components:
- DataCleaner: Main orchestrator class with single table output
- CountryNormalizer: Handles country name standardization
- DataValidator: Validates data quality and structure
- DatabaseManager: SQLite operations and schema management
"""

from .cleaner import DataCleaner
from .normalizers import CountryNormalizer, DataNormalizer
from .validators import DataValidator
from .database import DatabaseManager

__version__ = "2.0.0"
__all__ = [
    "DataCleaner", "CountryNormalizer", "DataNormalizer", 
    "DataValidator", "DatabaseManager"
]