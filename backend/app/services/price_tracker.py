"""
Price Tracker Service - Real-time price monitoring and historical data
Integrates with DexScreener, Birdeye, and Jupiter
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import requests

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('memecoin.services.price')


class PriceTracker:
    """Real-time price and metrics tracking (singleton for cache efficiency)"""
    
    _instance = None
    _cache = {}  # Class-level cache shared across all calls
    _cache_ttl = 30  # seconds
    
    @classmethod
    def instance(cls) -> "PriceTracker":
        """Get singleton instance (preserves cache across requests)"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        # Instance can still be created directly for testing
        pass
    
    @property
    def cache(self):
        return PriceTracker._cache
    
    @property
    def cache_ttl(self):
        return PriceTracker._cache_ttl
    
    def get_live_metrics(self, token_id: str) -> Dict[str, Any]:
        """
        Get live price and trading metrics for a token.
        Uses token_id to look up contract address, then fetches from DexScreener.
        """
        from .token_scanner import TokenScanner
        scanner = TokenScanner()
        token = scanner.get_token(token_id)
        
        if not token:
            return {"error": f"Token {token_id} not found"}
        
        return self.get_metrics_by_address(token.contract_address, token.chain)
    
    def get_metrics_by_address(self, address: str, chain: str = "solana") -> Dict[str, Any]:
        """Fetch live metrics for a contract address"""
        cache_key = f"{chain}:{address}"
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        try:
            url = f"{Config.DEXSCREENER_API_URL}/dex/tokens/{address}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code != 200:
                return {"error": f"API returned {resp.status_code}"}
            
            data = resp.json()
            pairs = data.get('pairs', [])
            
            if not pairs:
                return {"error": "No trading pairs found"}
            
            # Get the primary pair (highest liquidity)
            pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0) or 0))
            
            metrics = {
                "token_address": address,
                "chain": chain,
                "pair_address": pair.get('pairAddress', ''),
                "dex": pair.get('dexId', ''),
                "price_usd": float(pair.get('priceUsd', 0) or 0),
                "price_native": float(pair.get('priceNative', 0) or 0),
                "price_change": {
                    "5m": float(pair.get('priceChange', {}).get('m5', 0) or 0),
                    "1h": float(pair.get('priceChange', {}).get('h1', 0) or 0),
                    "6h": float(pair.get('priceChange', {}).get('h6', 0) or 0),
                    "24h": float(pair.get('priceChange', {}).get('h24', 0) or 0),
                },
                "volume": {
                    "5m": float(pair.get('volume', {}).get('m5', 0) or 0),
                    "1h": float(pair.get('volume', {}).get('h1', 0) or 0),
                    "6h": float(pair.get('volume', {}).get('h6', 0) or 0),
                    "24h": float(pair.get('volume', {}).get('h24', 0) or 0),
                },
                "txns": {
                    "5m": pair.get('txns', {}).get('m5', {}),
                    "1h": pair.get('txns', {}).get('h1', {}),
                    "6h": pair.get('txns', {}).get('h6', {}),
                    "24h": pair.get('txns', {}).get('h24', {}),
                },
                "liquidity_usd": float(pair.get('liquidity', {}).get('usd', 0) or 0),
                "market_cap": float(pair.get('marketCap', 0) or 0),
                "fdv": float(pair.get('fdv', 0) or 0),
                "pair_created_at": pair.get('pairCreatedAt', ''),
                "total_pairs": len(pairs),
                "updated_at": datetime.now().isoformat()
            }
            
            # Cache result
            self.cache[cache_key] = (time.time(), metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to fetch metrics for {address}: {e}")
            return {"error": str(e)}
    
    def get_price_history(self, address: str, chain: str = "solana",
                          timeframe: str = "24h") -> List[Dict[str, Any]]:
        """
        Get price history (candle data).
        Note: DexScreener free API has limited history. 
        For full history, Birdeye API is preferred.
        """
        try:
            if Config.BIRDEYE_API_KEY:
                return self._fetch_birdeye_history(address, timeframe)
            
            # Fallback: return current price snapshot only
            current = self.get_metrics_by_address(address, chain)
            return [{
                "timestamp": datetime.now().isoformat(),
                "price": current.get("price_usd", 0),
                "volume": current.get("volume", {}).get("24h", 0)
            }]
            
        except Exception as e:
            logger.error(f"Failed to get price history: {e}")
            return []
    
    def get_buy_sell_ratio(self, address: str, chain: str = "solana") -> Dict[str, Any]:
        """Calculate buy/sell ratio from transaction data"""
        metrics = self.get_metrics_by_address(address, chain)
        
        txns_24h = metrics.get("txns", {}).get("24h", {})
        buys = txns_24h.get("buys", 0)
        sells = txns_24h.get("sells", 0)
        total = buys + sells
        
        return {
            "buys_24h": buys,
            "sells_24h": sells,
            "total_24h": total,
            "buy_ratio": buys / total if total > 0 else 0.5,
            "sell_ratio": sells / total if total > 0 else 0.5,
            "pressure": "bullish" if buys > sells * 1.2 else ("bearish" if sells > buys * 1.2 else "neutral")
        }
    
    def _fetch_birdeye_history(self, address: str, timeframe: str) -> List[Dict[str, Any]]:
        """Fetch price history from Birdeye API"""
        try:
            # Map timeframe to Birdeye interval
            tf_map = {"1h": "1m", "6h": "5m", "24h": "15m", "7d": "1H"}
            interval = tf_map.get(timeframe, "15m")
            
            headers = {"X-API-KEY": Config.BIRDEYE_API_KEY}
            url = f"https://public-api.birdeye.so/defi/ohlcv?address={address}&type={interval}"
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            
            return [
                {
                    "timestamp": item.get("unixTime", 0),
                    "open": item.get("o", 0),
                    "high": item.get("h", 0),
                    "low": item.get("l", 0),
                    "close": item.get("c", 0),
                    "volume": item.get("v", 0),
                }
                for item in items
            ]
            
        except Exception as e:
            logger.error(f"Birdeye fetch failed: {e}")
            return []
