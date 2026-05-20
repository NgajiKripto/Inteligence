"""
GMGN Enrichment Service - Additional token data from GMGN API.
Provides rug ratio, bundler rate, wash trading detection, and fee data
not available from DexScreener alone.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional

import requests

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('memecoin.services.gmgn')

# Module-level cache
_gmgn_cache: Dict[str, tuple] = {}
_last_request_at: float = 0
CACHE_TTL = 300  # 5 minutes


class GmgnEnrichment:
    """GMGN API integration for enhanced token data"""

    def __init__(self):
        self.api_key = Config.GMGN_API_KEY if hasattr(Config, 'GMGN_API_KEY') else ''
        self.enabled = bool(self.api_key)
        self.request_delay = 2.5  # seconds between requests

    def enrich_token(self, mint: str) -> Optional[Dict[str, Any]]:
        """
        Fetch enhanced token data from GMGN.
        
        NOTE: This method has a built-in rate-limit delay. Do NOT call from
        the main request thread. Use only from background analysis tasks.

        Returns:
            - rug_ratio: probability of rug pull (0-1)
            - bundler_rate: % of bundled transactions
            - wash_trading: boolean
            - total_fee_sol: total fees generated
            - holder_count: number of holders
            - liquidity: USD liquidity
            - social_links: twitter, telegram, website
        """
        if not self.enabled:
            return None

        # Check cache
        if mint in _gmgn_cache:
            cached_at, cached_data = _gmgn_cache[mint]
            if time.time() - cached_at < CACHE_TTL:
                return cached_data

        # Rate limiting (non-blocking check - skip if too soon instead of sleeping)
        global _last_request_at
        elapsed = time.time() - _last_request_at
        if elapsed < self.request_delay:
            # Return cached data if available, otherwise skip
            if mint in _gmgn_cache:
                return _gmgn_cache[mint][1]
            logger.debug(f"GMGN rate limit: skipping {mint[:8]}... (next in {self.request_delay - elapsed:.1f}s)")
            return None

        try:
            url = "https://openapi.gmgn.ai/v1/token/info"
            params = {
                "chain": "sol",
                "address": mint,
                "timestamp": int(time.time()),
            }
            headers = {
                "X-APIKEY": self.api_key,
                "Content-Type": "application/json",
            }

            resp = requests.get(url, params=params, headers=headers, timeout=10)
            _last_request_at = time.time()

            if resp.status_code == 429:
                logger.warning("GMGN rate limited")
                return None

            if resp.status_code != 200:
                logger.warning(f"GMGN returned {resp.status_code}")
                return None

            payload = resp.json()
            data = payload.get("data", {}).get("data", payload.get("data", {}))

            result = {
                "source": "gmgn",
                "mint": mint,
                "rug_ratio": self._safe_float(data.get("rug_ratio")),
                "bundler_rate": self._safe_float(data.get("bundler_rate")),
                "is_wash_trading": bool(data.get("is_wash_trading")),
                "total_fee_sol": self._safe_float(data.get("total_fee")),
                "trade_fee_sol": self._safe_float(data.get("trade_fee")),
                "holder_count": int(data.get("holder_count", 0) or 0),
                "liquidity_usd": self._safe_float(data.get("liquidity")),
                "market_cap_usd": self._safe_float(data.get("market_cap") or data.get("mcap")),
                "price_usd": self._safe_float(data.get("price")),
                "smart_degen_count": int(data.get("smart_degen_count", 0) or 0),
                "social_links": {
                    "twitter": data.get("link", {}).get("twitter_username", ""),
                    "telegram": data.get("link", {}).get("telegram", ""),
                    "website": data.get("link", {}).get("website", ""),
                },
                "updated_at": datetime.now().isoformat(),
            }

            # Cache
            _gmgn_cache[mint] = (time.time(), result)
            return result

        except Exception as e:
            logger.error(f"GMGN enrichment failed for {mint[:8]}...: {e}")
            return None

    def get_trending(self, interval: str = "5m", limit: int = 50) -> list:
        """Fetch GMGN trending tokens"""
        if not self.enabled:
            return []

        try:
            url = "https://openapi.gmgn.ai/v1/market/rank"
            params = {
                "chain": "sol",
                "interval": interval,
                "limit": limit,
                "order_by": "volume",
                "direction": "desc",
                "timestamp": int(time.time()),
            }
            headers = {
                "X-APIKEY": self.api_key,
                "Content-Type": "application/json",
            }

            resp = requests.get(url, params=params, headers=headers, timeout=10)
            _last_request_at = time.time()

            if resp.status_code != 200:
                return []

            payload = resp.json()
            rows = (
                payload.get("data", {}).get("data", {}).get("rank") or
                payload.get("data", {}).get("rank") or
                payload.get("data", {}).get("data") or
                []
            )

            return rows if isinstance(rows, list) else []

        except Exception as e:
            logger.error(f"GMGN trending failed: {e}")
            return []

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Safely convert to float"""
        if value is None:
            return None
        try:
            f = float(value)
            return f if f == f else None  # NaN check
        except (ValueError, TypeError):
            return None
