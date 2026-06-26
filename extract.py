"""
Data extraction module with retry logic and error handling.
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from src.api.client import StockAPIClient
from src.config import settings

class Extractor:
    """Extracts stock data from various APIs."""
    
    def __init__(self):
        self.client = StockAPIClient()
        self.extracted_data = []
        self.failed_stocks = []
    
    async def extract_stock_data(self, symbols: List[str]) -> List[Dict]:
        """
        Extract stock data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            List of extracted stock data
        """
        logger.info(f"Extracting data for {len(symbols)} stocks")
        
        if not symbols:
            logger.warning("No symbols provided for extraction")
            return []
        
        try:
            async with self.client as client:
                results = await client.fetch_multiple_stocks(symbols)
            
            # Process results
            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Extraction error: {str(result)}")
                    continue
                if result and result.get("data"):
                    valid_results.append(result)
                else:
                    logger.warning(f"No data for {result.get('symbol', 'unknown')}")
            
            self.extracted_data = valid_results
            logger.info(f"Successfully extracted {len(valid_results)} stocks")
            
            # Log sample
            if valid_results:
                sample = valid_results[0]
                logger.debug(f"Sample data: {sample['symbol']} - {len(sample['data'])} records")
            
            return valid_results
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            raise
    
    async def extract_single_stock(self, symbol: str) -> Optional[Dict]:
        """
        Extract data for a single stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Stock data or None if failed
        """
        try:
            async with self.client as client:
                result = await client.fetch_stock_data(symbol)
                if result and result.get("data"):
                    return result
                return None
        except Exception as e:
            logger.error(f"Failed to extract {symbol}: {str(e)}")
            return None
    
    def get_extraction_stats(self) -> Dict:
        """
        Get extraction statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_extracted": len(self.extracted_data),
            "failed_stocks": self.failed_stocks,
            "total_records": sum(len(stock["data"]) for stock in self.extracted_data)
        }