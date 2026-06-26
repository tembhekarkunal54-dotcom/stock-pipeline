"""
Main application entry point for the Stock Pipeline.
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime
import argparse

from src.config import settings
from src.etl.extract import Extractor
from src.etl.transform import Transformer
from src.etl.load import Loader
from src.anomaly.detector import AnomalyDetector
from src.anomaly.alert import AlertSystem

# Setup logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True
)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time} | {level} | {name}:{function} - {message}"
)
logger.add(
    "logs/errors_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="ERROR",
    format="{time} | {level} | {name}:{function} - {message}"
)

class StockPipeline:
    """Main pipeline orchestrator."""
    
    def __init__(self):
        self.extractor = Extractor()
        self.transformer = Transformer()
        self.loader = Loader()
        self.detector = AnomalyDetector(
            contamination=settings.ISOLATION_FOREST_CONTAMINATION
        )
        self.alert_system = AlertSystem()
        self.start_time = None
        self.end_time = None
    
    async def run(self, symbols: list = None):
        """
        Run the complete pipeline.
        
        Args:
            symbols: List of stock symbols to process
        """
        if symbols is None:
            symbols = settings.DEFAULT_SYMBOLS
        
        self.start_time = datetime.now()
        logger.info("🚀 Starting Stock Pipeline...")
        logger.info(f"📊 Processing {len(symbols)} stocks: {', '.join(symbols)}")
        logger.info(f"⏰ Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 50)
        
        try:
            # Step 1: Extract data
            logger.info("📥 Step 1: Extracting data from APIs...")
            raw_data = await self.extractor.extract_stock_data(symbols)
            
            if not raw_data:
                logger.warning("⚠️ No data extracted from APIs")
                return
            
            logger.info(f"✅ Extracted data for {len(raw_data)} stocks")
            
            # Step 2: Transform data
            logger.info("🔄 Step 2: Transforming and validating data...")
            df = self.transformer.transform_data(raw_data)
            
            if df.empty:
                logger.warning("⚠️ No data after transformation")
                return
            
            logger.info(f"✅ Transformed {len(df)} rows of data")
            
            # Step 3: Load data
            logger.info("💾 Step 3: Loading data to database...")
            self.loader.load_data(df)
            logger.info("✅ Data loaded successfully")
            
            # Step 4: Detect anomalies
            if settings.ENABLE_ANOMALY_DETECTION:
                logger.info("🔍 Step 4: Detecting anomalies...")
                df_with_anomalies = self.detector.detect_anomalies(df)
                anomaly_count = df_with_anomalies["is_anomaly"].sum()
                
                if anomaly_count > 0:
                    logger.warning(f"⚠️ Found {anomaly_count} anomalies")
                    
                    # Send alerts
                    if settings.ENABLE_ALERTS:
                        logger.info("📧 Step 5: Sending alerts...")
                        anomalies = df_with_anomalies[
                            df_with_anomalies["is_anomaly"] == True
                        ]
                        anomaly_list = []
                        for _, row in anomalies.iterrows():
                            anomaly_list.append({
                                "symbol": row["symbol"],
                                "date": row["date"].strftime("%Y-%m-%d"),
                                "price": row["close"],
                                "change": row["price_change"],
                                "score": row["anomaly_score"]
                            })
                        await self.alert_system.send_batch_alert(anomaly_list)
                        logger.info("✅ Alerts sent")
                else:
                    logger.info("✅ No anomalies detected")
            
            # Pipeline complete
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            logger.info("-" * 50)
            logger.info("✅ Pipeline completed successfully!")
            logger.info(f"⏱️  Total duration: {duration:.2f} seconds")
            logger.info(f"📊 Total records: {len(df)}")
            logger.info(f"📈 Total stocks: {len(df['symbol'].unique())}")
            
            # Return summary
            return {
                "status": "success",
                "duration": duration,
                "records": len(df),
                "stocks": len(df["symbol"].unique()),
                "anomalies": anomaly_count if settings.ENABLE_ANOMALY_DETECTION else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            logger.exception(e)
            
            # Send critical alert
            if settings.ENABLE_ALERTS:
                await self.alert_system.send_alert(
                    f"🚨 Pipeline failed: {str(e)}",
                    severity="critical"
                )
            
            return {
                "status": "failed",
                "error": str(e)
            }

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Stock Pipeline - ETL for stock market data"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Stock symbols to process (e.g., AAPL GOOGL MSFT)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run pipeline once and exit"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Start the dashboard after pipeline"
    )
    parser.add_argument(
        "--config",
        help="Path to custom config file"
    )
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    
    # Initialize pipeline
    pipeline = StockPipeline()
    
    # Run pipeline
    symbols = args.symbols if args.symbols else None
    result = await pipeline.run(symbols)
    
    # Start dashboard if requested
    if args.dashboard and result.get("status") == "success":
        logger.info("📊 Starting dashboard...")
        import subprocess
        subprocess.Popen(["streamlit", "run", "src/dashboard/app.py"])
    
    return result

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info(f"📊 Final result: {result}")
    except KeyboardInterrupt:
        logger.info("👋 Pipeline stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        sys.exit(1)