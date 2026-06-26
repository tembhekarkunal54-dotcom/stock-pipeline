"""
Anomaly detection using Isolation Forest.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from loguru import logger

class AnomalyDetector:
    """Detects anomalies in stock data."""
    
    def __init__(self, contamination: float = 0.1):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies in stock data."""
        if df.empty:
            return df
        
        df = df.copy()
        features = self._prepare_features(df)
        
        if not self.is_fitted:
            scaled_features = self.scaler.fit_transform(features)
            self.model.fit(scaled_features)
            self.is_fitted = True
        else:
            scaled_features = self.scaler.transform(features)
        
        predictions = self.model.predict(scaled_features)
        df["is_anomaly"] = predictions == -1
        df["anomaly_score"] = self.model.score_samples(scaled_features)
        
        anomaly_count = df["is_anomaly"].sum()
        logger.info(f"Detected {anomaly_count} anomalies")
        
        return df
    
    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare features for anomaly detection."""
        features = []
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol].sort_values("date")
            for _, row in symbol_data.iterrows():
                feature_row = [
                    row["price_change"] if pd.notna(row["price_change"]) else 0,
                    row["volume_change"] if pd.notna(row["volume_change"]) else 0,
                    row["daily_range_pct"] if pd.notna(row["daily_range_pct"]) else 0,
                ]
                features.append(feature_row)
        return np.array(features)