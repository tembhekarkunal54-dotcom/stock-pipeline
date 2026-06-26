"""
Data loading module.
"""
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger
from src.config import settings

class Loader:
    """Loads data into database."""
    
    def __init__(self):
        self.engine = create_engine(settings.DB_URL)
        self.Session = sessionmaker(bind=self.engine)
    
    def load_data(self, df: pd.DataFrame, table_name: str = "stock_prices"):
        """Load DataFrame to database."""
        if df.empty:
            logger.warning("No data to load")
            return
        
        # ✅ Remove columns that don't exist in database
        columns_to_drop = ["price_change_abs", "daily_range", "daily_range_pct", "volume_change"]
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])
                logger.debug(f"Dropped column: {col}")
        
        logger.info(f"Loading {len(df)} rows to {table_name}")
        
        with self.engine.begin() as connection:
            self._create_table_if_not_exists(connection, table_name)
            
            df.to_sql(
                table_name,
                connection,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000
            )
        
        logger.info(f"✅ Successfully loaded data to {table_name}")
    
    def _create_table_if_not_exists(self, connection, table_name: str):
        """Create table if it doesn't exist."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            open DECIMAL(12, 4),
            high DECIMAL(12, 4),
            low DECIMAL(12, 4),
            close DECIMAL(12, 4),
            volume BIGINT,
            price_change DECIMAL(12, 4),
            day_of_week INTEGER,
            month INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        );
        """
        connection.execute(text(create_table_sql))