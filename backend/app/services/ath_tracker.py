"""
ATH/Range Context Tracker - Detects top-blast risk and ATH distance.
Inspired by Charon's chart context that warns about late entries.
"""

from datetime import datetime
from typing import Dict, Any, Optional

import requests

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('memecoin.services.ath')


class AthTracker:
    """Tracks All-Time-High context and top-blast risk for tokens"""

    def get_ath_context(self, address: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Get ATH/range context for a token.
        
        Returns:
            - current_price: current price
            - range_high: highest price in lookback period
            - distance_from_ath_pct: how far below ATH (negative = below)
            - top_blast_risk: True if price is >85% of range high (late entry warning)
            - range_context: 24h high/low/volume summary
        """
        try:
            # Use DexScreener for price change data
            url = f"{Config.DEXSCREENER_API_URL}/dex/tokens/{address}"
            resp = requests.get(url, timeout=10)

            if resp.status_code != 200:
                return {"error": "Failed to fetch price data"}

            data = resp.json()
            pairs = data.get("pairs", [])
            if not pairs:
                return {"error": "No pairs found"}

            pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0) or 0))

            current_price = float(pair.get("priceUsd", 0) or 0)
            price_change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)

            # Estimate 24h high/low from percentage changes.
            # NOTE: This is an approximation. DexScreener only provides period-end changes,
            # not intraday highs. For tokens that pumped and dumped within 24h, the actual
            # ATH may be higher than estimated here. Flag this limitation in results.
            #
            # Math: if current = start * (1 + change/100), then start = current / (1 + change/100)
            # The start-of-period price is a proxy for the other extreme.
            if price_change_24h > 0:
                # Price went up: start was lower, current is at/near high
                estimated_period_start = current_price / (1 + price_change_24h / 100)
                estimated_24h_low = estimated_period_start
                estimated_24h_high = current_price
            elif price_change_24h < 0:
                # Price went down: start was higher (this is the estimated 24h high)
                estimated_period_start = current_price / (1 + price_change_24h / 100)
                estimated_24h_low = current_price
                estimated_24h_high = estimated_period_start
            else:
                estimated_24h_low = current_price
                estimated_24h_high = current_price

            # Use 6h change to refine: if 6h change differs from 24h, price moved intraday
            price_change_6h = float(pair.get("priceChange", {}).get("h6", 0) or 0)
            if price_change_6h != 0:
                estimated_6h_start = current_price / (1 + price_change_6h / 100)
                # The max of all estimated start prices gives better ATH approximation
                estimated_24h_high = max(estimated_24h_high, estimated_6h_start, current_price)

            range_high = max(current_price, estimated_24h_high)
            range_low = min(current_price, estimated_24h_low) if estimated_24h_low > 0 else current_price

            # Distance from ATH
            distance_from_ath_pct = ((current_price / range_high) - 1) * 100 if range_high > 0 else 0

            # Top blast risk: price is within 15% of range high
            top_blast_risk = (current_price / range_high >= 0.85) if range_high > 0 else False

            volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)

            return {
                "token_address": address,
                "chain": chain,
                "current_price": current_price,
                "range_high_24h": range_high,
                "range_low_24h": range_low,
                "distance_from_ath_pct": round(distance_from_ath_pct, 2),
                "top_blast_risk": top_blast_risk,
                "near_ath": distance_from_ath_pct > -5,
                "at_dip": distance_from_ath_pct < -30,
                "volume_24h": volume_24h,
                "price_change_24h": price_change_24h,
                "risk_assessment": self._assess_entry_risk(distance_from_ath_pct, top_blast_risk),
                "updated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"ATH context failed for {address}: {e}")
            return {"error": str(e)}

    def _assess_entry_risk(self, distance_from_ath_pct: float, top_blast_risk: bool) -> str:
        """Assess entry timing risk based on ATH distance"""
        if top_blast_risk:
            return "HIGH - Near ATH, potential late entry. Wait for pullback."
        elif distance_from_ath_pct > -5:
            return "ELEVATED - Close to recent high. Entry risk moderate."
        elif distance_from_ath_pct < -50:
            return "LOW - Significant pullback. Good entry if fundamentals hold."
        elif distance_from_ath_pct < -30:
            return "LOW-MODERATE - Meaningful dip from ATH. Potential value entry."
        else:
            return "MODERATE - Mid-range. Check other indicators."
