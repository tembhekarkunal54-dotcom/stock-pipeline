"""
Stock Pipeline - Intelligent Stock Market Data Pipeline

A production-ready ETL pipeline for stock market data with:
- Async API integration
- Data quality validation
- Anomaly detection
- Real-time dashboard
- Alert system
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Package exports
from src.config import Settings
from src.api.client import StockAPIClient
from src.etl.extract import Extractor
from src.etl.transform import Transformer
from src.etl.load import Loader
from src.anomaly.detector import AnomalyDetector
from src.anomaly.alert import AlertSystem

__all__ = [
    "Settings",
    "StockAPIClient",
    "Extractor",
    "Transformer",
    "Loader",
    "AnomalyDetector",
    "AlertSystem",
]