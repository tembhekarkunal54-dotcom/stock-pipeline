"""
Configuration management using Pydantic Settings.
All environment variables are validated at startup.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
from pathlib import Path
import os

class Settings(BaseSettings):
    """Application settings with validation."""
    
    # API Configuration
    ALPHA_VANTAGE_KEY: str = Field(..., env="ALPHA_VANTAGE_KEY")
    YAHOO_FINANCE_KEY: Optional[str] = Field(None, env="YAHOO_FINANCE_KEY")
    API_BASE_URL: str = Field(
        "https://www.alphavantage.co/query",
        env="API_BASE_URL"
    )
    
    # Database Configuration
    DB_URL: str = Field(
        "sqlite:///stock_data.db",
        env="DB_URL"
    )
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    
    # Application Configuration
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    MAX_RETRIES: int = Field(3, env="MAX_RETRIES")
    REQUEST_TIMEOUT: int = Field(30, env="REQUEST_TIMEOUT")
    MAX_CONCURRENT_REQUESTS: int = Field(10, env="MAX_CONCURRENT_REQUESTS")
    
    # Stocks to Track
    DEFAULT_SYMBOLS: List[str] = Field(
        ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA"],
        env="DEFAULT_SYMBOLS"
    )
    
    # Data Quality Thresholds
    MIN_VOLUME_THRESHOLD: int = Field(1000, env="MIN_VOLUME_THRESHOLD")
    MAX_VOLATILITY_THRESHOLD: float = Field(0.5, env="MAX_VOLATILITY_THRESHOLD")
    MIN_DATA_POINTS: int = Field(5, env="MIN_DATA_POINTS")
    
    # Alert Configuration
    SLACK_WEBHOOK_URL: Optional[str] = Field(None, env="SLACK_WEBHOOK_URL")
    EMAIL_SENDER: Optional[str] = Field(None, env="EMAIL_SENDER")
    EMAIL_PASSWORD: Optional[str] = Field(None, env="EMAIL_PASSWORD")
    EMAIL_RECIPIENTS: List[str] = Field(
        ["admin@example.com"],
        env="EMAIL_RECIPIENTS"
    )
    
    # Feature Flags
    ENABLE_ANOMALY_DETECTION: bool = Field(True, env="ENABLE_ANOMALY_DETECTION")
    ENABLE_ALERTS: bool = Field(True, env="ENABLE_ALERTS")
    ENABLE_DASHBOARD: bool = Field(True, env="ENABLE_DASHBOARD")
    
    # Model Configuration
    ISOLATION_FOREST_CONTAMINATION: float = Field(0.1, env="ISOLATION_FOREST_CONTAMINATION")
    ANOMALY_SCORE_THRESHOLD: float = Field(-0.5, env="ANOMALY_SCORE_THRESHOLD")
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    @validator("DB_URL")
    def validate_db_url(cls, v):
        """Ensure database URL is valid."""
        if not v.startswith(("postgresql://", "sqlite://", "mysql://")):
            raise ValueError("DB_URL must start with postgresql://, sqlite://, or mysql://")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables

# Create global settings instance
settings = Settings()

# Create necessary directories
def create_directories():
    """Create necessary directories if they don't exist."""
    directories = ["logs", "data"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

create_directories()