"""
Async API client for financial data with retry logic and rate limiting.
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)
from loguru import logger
from src.config import settings
from src.api.rate_limiter import RateLimiter

class StockAPIClient:
    """Asynchronous client for stock market APIs."""
    
    def __init__(self):
        self.api_key = settings.ALPHA_VANTAGE_KEY
        self.base_url = settings.API_BASE_URL
        self.rate_limiter = RateLimiter(requests_per_second=5)
        self.session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
    
    async def __aenter__(self):
        """Context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=self._timeout,
            headers={
                "User-Agent": "StockPipeline/1.0",
                "Accept": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError, aiohttp.ServerDisconnectedError)
        ),
        reraise=True
    )
    async def fetch_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch stock data for a given symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            Dictionary containing stock data
            
        Raises:
            ValueError: If API returns an error
            aiohttp.ClientError: If network error occurs
        """
        await self.rate_limiter.acquire()
        
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": "compact"
        }
        
        logger.debug(f"Fetching data for {symbol}")
        
        try:
            async with self.session.get(
                self.base_url,
                params=params,
                ssl=False  # Only for development
            ) as response:
                # Check status
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API error for {symbol}: {response.status} - {error_text}")
                    raise ValueError(f"API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                # Check for API error messages
                if "Error Message" in data:
                    raise ValueError(f"API Error: {data['Error Message']}")
                
                if "Note" in data:
                    # Rate limit warning
                    logger.warning(f"Rate limit note for {symbol}: {data['Note']}")
                    await asyncio.sleep(60)  # Wait a minute
                    return await self.fetch_stock_data(symbol)
                
                # Transform the response
                transformed = self._transform_response(data, symbol)
                
                # Validate data
                if not transformed.get("data"):
                    logger.warning(f"No data available for {symbol}")
                    return {"symbol": symbol, "data": []}
                
                return transformed
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {symbol} after {settings.REQUEST_TIMEOUT}s")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Client error fetching {symbol}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {symbol}: {str(e)}")
            raise
    
    def _transform_response(self, data: Dict, symbol: str) -> Dict:
        """
        Transform raw API response into standard format.
        
        Args:
            data: Raw API response
            symbol: Stock symbol
            
        Returns:
            Standardized stock data
        """
        time_series = data.get("Time Series (Daily)", {})
        
        if not time_series:
            logger.warning(f"No time series data for {symbol}")
            return {"symbol": symbol, "data": []}
        
        # Get latest data (up to 30 days)
        dates = sorted(time_series.keys(), reverse=True)[:30]
        
        stock_data = []
        for date in dates:
            daily = time_series[date]
            stock_data.append({
                "date": date,
                "open": float(daily.get("1. open", 0)),
                "high": float(daily.get("2. high", 0)),
                "low": float(daily.get("3. low", 0)),
                "close": float(daily.get("4. close", 0)),
                "volume": int(daily.get("5. volume", 0))
            })
        
        logger.debug(f"Transformed {len(stock_data)} records for {symbol}")
        
        return {
            "symbol": symbol,
            "data": stock_data,
            "last_updated": datetime.now().isoformat(),
            "source": "Alpha Vantage"
        }
    
    async def fetch_multiple_stocks(self, symbols: List[str]) -> List[Dict]:
        """
        Fetch data for multiple stocks concurrently.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            List of stock data dictionaries
        """
        logger.info(f"Fetching data for {len(symbols)} stocks")
        
        tasks = [self.fetch_stock_data(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        valid_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {symbols[i]}: {str(result)}")
                failed_results.append({
                    "symbol": symbols[i],
                    "error": str(result)
                })
            else:
                valid_results.append(result)
        
        if failed_results:
            logger.warning(f"Failed to fetch {len(failed_results)} stocks")
        
        # Store failed stocks for retry
        self.failed_stocks = failed_results
        
        return valid_results
    
    async def get_stock_quote(self, symbol: str) -> Dict:
        """
        Get real-time quote for a stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Real-time quote data
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        await self.rate_limiter.acquire()
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                quote = data.get("Global Quote", {})
                
                if not quote:
                    return {}
                
                return {
                    "symbol": quote.get("01. symbol"),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "0%"),
                    "volume": int(quote.get("06. volume", 0)),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            return {}