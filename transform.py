"""
Data transformation and quality validation.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
from loguru import logger

from src.config import settings

class Transformer:
    """Transforms raw stock data with quality checks."""
    
    def __init__(self):
        self.transformation_stats = {
            "rows_before": 0,
            "rows_after": 0,
            "quality_checks_passed": 0,
            "quality_checks_failed": 0
        }
    
    def transform_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Transform raw API data into clean DataFrame."""
        if not raw_data:
            logger.warning("No data to transform")
            return pd.DataFrame()
        
        logger.info(f"Transforming data for {len(raw_data)} stocks")
        
        df = self._flatten_data(raw_data)
        self.transformation_stats["rows_before"] = len(df)
        
        if df.empty:
            logger.warning("Empty DataFrame after flattening")
            return df
        
        df = self._add_features(df)
        quality_report = self._validate_data(df)
        self.transformation_stats["quality_checks_passed"] = quality_report["passed"]
        self.transformation_stats["quality_checks_failed"] = quality_report["failed"]
        
        df = self._clean_data(df)
        self.transformation_stats["rows_after"] = len(df)
        
        logger.info(f"Transformed {len(df)} rows of data")
        return df
    
    def _flatten_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Flatten nested API response into DataFrame."""
        records = []
        for stock in raw_data:
            if not stock.get("data"):
                continue
            symbol = stock["symbol"]
            for daily in stock["data"]:
                try:
                    records.append({
                        "symbol": symbol,
                        "date": datetime.strptime(daily["date"], "%Y-%m-%d"),
                        "open": float(daily["open"]),
                        "high": float(daily["high"]),
                        "low": float(daily["low"]),
                        "close": float(daily["close"]),
                        "volume": int(daily["volume"])
                    })
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid record: {str(e)}")
                    continue
        return pd.DataFrame(records)
    
    def _add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add calculated features for analysis."""
        df = df.copy()
        df = df.sort_values(["symbol", "date"])
        
        df["price_change"] = df.groupby("symbol")["close"].pct_change()
        df["price_change_abs"] = df["price_change"].abs()
        df["volume_change"] = df.groupby("symbol")["volume"].pct_change()
        df["daily_range"] = df["high"] - df["low"]
        df["daily_range_pct"] = df["daily_range"] / df["close"]
        df["day_of_week"] = df["date"].dt.dayofweek
        df["month"] = df["date"].dt.month
        
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> Dict[str, int]:
        """Validate data quality (simplified)."""
        try:
            passed = 0
            failed = 0
            
            # Check for required columns
            required_cols = ["symbol", "date", "close", "volume"]
            for col in required_cols:
                if col in df.columns and not df[col].isnull().any():
                    passed += 1
                else:
                    failed += 1
            
            # Check data types
            if "close" in df.columns and (df["close"] > 0).all():
                passed += 1
            else:
                failed += 1
                
            if "volume" in df.columns and (df["volume"] >= 0).all():
                passed += 1
            else:
                failed += 1
            
            return {"passed": passed, "failed": failed}
            
        except Exception as e:
            logger.warning(f"Validation error: {str(e)}")
            return {"passed": 0, "failed": 0}
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove invalid rows and handle nulls."""
        df = df.copy()
        if df.empty:
            return df
        
        # Remove rows with missing critical values
        df = df.dropna(subset=["symbol", "date", "close", "volume"])
        
        # Remove rows with zero or negative values
        df = df[df["volume"] > 0]
        df = df[df["close"] > 0]
        df = df[df["open"] > 0]
        df = df[df["high"] > 0]
        df = df[df["low"] > 0]
        
        # Remove outliers (3 standard deviations)
        for col in ["price_change", "volume_change"]:
            if col in df.columns:
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    df = df[abs(df[col] - mean) <= 3 * std]
        
        # Fill nulls
        for col in df.columns:
            if df[col].isnull().any():
                if col in ["price_change", "volume_change"]:
                    df[col] = df[col].fillna(0)
                else:
                    df[col] = df[col].fillna(df[col].median() if not df[col].isnull().all() else 0)
        
        return df