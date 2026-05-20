"""
Strategy Manager - Configurable analysis profiles inspired by Charon's strategy system.
Supports multiple trading analysis modes with different parameter sets.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..config import Config
from ..utils.logger import get_logger
from ..utils import atomic_write_json

logger = get_logger('memecoin.services.strategy')


# Default strategy definitions
DEFAULT_STRATEGIES = {
    "sniper": {
        "id": "sniper",
        "name": "Sniper",
        "description": "New token entry. Fee-claim overlap signals, tight mcap range, fast response.",
        "enabled": True,
        "params": {
            "min_mcap_usd": 7000,
            "max_mcap_usd": 200000,
            "min_liquidity_usd": 5000,
            "min_holders": 0,
            "max_top10_holder_pct": 80,
            "min_volume_24h": 1000,
            "max_token_age_hours": 1,
            "require_mint_disabled": True,
            "require_lp_locked": False,
            "min_overlap_signals": 2,
            "use_llm": True,
            "llm_min_confidence": 50,
            "simulation_agents": 30,
            "simulation_rounds": 5,
            "suggested_tp_pct": 50,
            "suggested_sl_pct": -25,
            "trailing_enabled": True,
            "trailing_pct": 20,
        }
    },
    "dip_buy": {
        "id": "dip_buy",
        "name": "Dip Buy",
        "description": "Wait for ATH distance dip. Larger mcap tokens that pulled back significantly.",
        "enabled": False,
        "params": {
            "min_mcap_usd": 25000,
            "max_mcap_usd": 500000,
            "min_liquidity_usd": 20000,
            "min_holders": 100,
            "max_top10_holder_pct": 60,
            "min_volume_24h": 10000,
            "max_token_age_hours": 24,
            "require_mint_disabled": True,
            "require_lp_locked": True,
            "min_overlap_signals": 1,
            "max_ath_distance_pct": -40,
            "use_llm": True,
            "llm_min_confidence": 60,
            "simulation_agents": 50,
            "simulation_rounds": 8,
            "suggested_tp_pct": 30,
            "suggested_sl_pct": -20,
            "trailing_enabled": True,
            "trailing_pct": 15,
        }
    },
    "smart_money": {
        "id": "smart_money",
        "name": "Smart Money",
        "description": "Follow smart money. Strict holder quality, high liquidity, wallet overlap required.",
        "enabled": False,
        "params": {
            "min_mcap_usd": 10000,
            "max_mcap_usd": 1000000,
            "min_liquidity_usd": 50000,
            "min_holders": 1000,
            "max_top10_holder_pct": 50,
            "min_volume_24h": 50000,
            "max_token_age_hours": 24,
            "require_mint_disabled": True,
            "require_lp_locked": True,
            "min_overlap_signals": 2,
            "min_smart_wallet_overlap": 2,
            "use_llm": True,
            "llm_min_confidence": 70,
            "simulation_agents": 50,
            "simulation_rounds": 10,
            "suggested_tp_pct": 100,
            "suggested_sl_pct": -25,
            "trailing_enabled": False,
            "partial_tp_enabled": True,
            "partial_tp_at_pct": 100,
            "partial_tp_sell_pct": 50,
        }
    },
    "degen": {
        "id": "degen",
        "name": "Degen",
        "description": "Rule-based only. Lower thresholds, no LLM, fast decisions for high-risk plays.",
        "enabled": False,
        "params": {
            "min_mcap_usd": 5000,
            "max_mcap_usd": 100000,
            "min_liquidity_usd": 2000,
            "min_holders": 0,
            "max_top10_holder_pct": 100,
            "min_volume_24h": 500,
            "max_token_age_hours": 1,
            "require_mint_disabled": False,
            "require_lp_locked": False,
            "min_overlap_signals": 1,
            "use_llm": False,
            "llm_min_confidence": 0,
            "simulation_agents": 20,
            "simulation_rounds": 3,
            "suggested_tp_pct": 30,
            "suggested_sl_pct": -15,
            "trailing_enabled": True,
            "trailing_pct": 10,
            "max_rug_ratio": 0.5,
            "max_bundler_rate": 0.7,
        }
    }
}


class StrategyManager:
    """Manages analysis strategy profiles"""

    def __init__(self):
        self.data_file = os.path.join(Config.DATA_DIR, 'strategies.json')
        self._ensure_defaults()

    def get_active_strategy(self) -> Dict[str, Any]:
        """Get the currently active strategy"""
        strategies = self._load_strategies()
        for strat in strategies.values():
            if strat.get("enabled"):
                return strat
        # Fallback to sniper
        return strategies.get("sniper", DEFAULT_STRATEGIES["sniper"])

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific strategy by ID"""
        strategies = self._load_strategies()
        return strategies.get(strategy_id)

    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all available strategies"""
        strategies = self._load_strategies()
        return list(strategies.values())

    def set_active_strategy(self, strategy_id: str) -> bool:
        """Set the active strategy"""
        strategies = self._load_strategies()
        if strategy_id not in strategies:
            return False

        for sid in strategies:
            strategies[sid]["enabled"] = (sid == strategy_id)

        self._save_strategies(strategies)
        logger.info(f"Active strategy set to: {strategy_id}")
        return True

    def update_strategy_param(self, strategy_id: str, key: str, value: Any) -> bool:
        """Update a specific parameter of a strategy"""
        strategies = self._load_strategies()
        if strategy_id not in strategies:
            return False

        if "params" not in strategies[strategy_id]:
            strategies[strategy_id]["params"] = {}

        strategies[strategy_id]["params"][key] = value
        self._save_strategies(strategies)
        return True

    def filter_by_strategy(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply active strategy filters to token data.
        Returns pass/fail with reasons.
        """
        strat = self.get_active_strategy()
        params = strat.get("params", {})
        failures = []

        metrics = token_data.get("metrics", {})
        on_chain = token_data.get("on_chain", {})
        overlap = token_data.get("overlap", {})
        gmgn = token_data.get("gmgn", {})
        wallet_overlap = token_data.get("wallet_overlap", {})

        # Market cap
        mcap = metrics.get("market_cap", 0)
        if params.get("min_mcap_usd", 0) > 0 and mcap < params["min_mcap_usd"]:
            failures.append(f"mcap ${mcap:,.0f} < min ${params['min_mcap_usd']:,.0f}")
        if params.get("max_mcap_usd", 0) > 0 and mcap > params["max_mcap_usd"]:
            failures.append(f"mcap ${mcap:,.0f} > max ${params['max_mcap_usd']:,.0f}")

        # Liquidity
        liq = metrics.get("liquidity_usd", 0)
        if params.get("min_liquidity_usd", 0) > 0 and liq < params["min_liquidity_usd"]:
            failures.append(f"liquidity ${liq:,.0f} < min ${params['min_liquidity_usd']:,.0f}")

        # Holders
        holders = metrics.get("holders_count", 0)
        if params.get("min_holders", 0) > 0 and holders < params["min_holders"]:
            failures.append(f"holders {holders} < min {params['min_holders']}")

        # Volume
        vol = metrics.get("volume_24h", 0)
        if params.get("min_volume_24h", 0) > 0 and vol < params["min_volume_24h"]:
            failures.append(f"volume ${vol:,.0f} < min ${params['min_volume_24h']:,.0f}")

        # Contract safety
        if params.get("require_mint_disabled") and on_chain.get("is_mint_disabled") is False:
            failures.append("mint authority not disabled (required)")
        if params.get("require_lp_locked") and on_chain.get("lp_locked") is False:
            failures.append("LP not locked (required)")

        # Top holder concentration
        top10_pct = metrics.get("top10_holders_pct", 0)
        if params.get("max_top10_holder_pct", 100) < 100 and top10_pct > params["max_top10_holder_pct"]:
            failures.append(f"top10 holders {top10_pct:.0f}% > max {params['max_top10_holder_pct']}%")

        # Token age
        max_age_hours = params.get("max_token_age_hours", 0)
        if max_age_hours > 0:
            token_age_hours = metrics.get("token_age_hours", 0)
            if token_age_hours > max_age_hours:
                failures.append(f"token age {token_age_hours:.0f}h > max {max_age_hours}h")

        # Signal overlap
        min_overlap = params.get("min_overlap_signals", 0)
        if min_overlap > 0:
            overlap_count = overlap.get("overlap_count", 0) if isinstance(overlap, dict) else 0
            if overlap_count < min_overlap:
                failures.append(f"signal overlap {overlap_count} < min {min_overlap}")

        # Smart wallet overlap
        min_smart = params.get("min_smart_wallet_overlap", 0)
        if min_smart > 0:
            smart_count = wallet_overlap.get("overlap_count", 0) if isinstance(wallet_overlap, dict) else 0
            if smart_count < min_smart:
                failures.append(f"smart wallet overlap {smart_count} < min {min_smart}")

        # ATH distance (for dip buy)
        max_ath_dist = params.get("max_ath_distance_pct", 0)
        if max_ath_dist < 0:
            ath_dist = metrics.get("distance_from_ath_pct", 0)
            if ath_dist > max_ath_dist:
                failures.append(f"ATH distance {ath_dist:.0f}% > target {max_ath_dist}%")

        # GMGN rug ratio
        max_rug = params.get("max_rug_ratio", 0)
        if max_rug > 0 and gmgn:
            rug_ratio = gmgn.get("rug_ratio") or 0
            if rug_ratio > max_rug:
                failures.append(f"rug ratio {rug_ratio:.2f} > max {max_rug}")

        # GMGN bundler rate
        max_bundler = params.get("max_bundler_rate", 0)
        if max_bundler > 0 and gmgn:
            bundler_rate = gmgn.get("bundler_rate") or 0
            if bundler_rate > max_bundler:
                failures.append(f"bundler rate {bundler_rate:.2f} > max {max_bundler}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "strategy_id": strat["id"],
            "strategy_name": strat["name"],
        }

    def _ensure_defaults(self):
        """Ensure default strategies exist"""
        if not os.path.exists(self.data_file):
            self._save_strategies(DEFAULT_STRATEGIES)

    def _load_strategies(self) -> Dict[str, Dict]:
        """Load strategies from disk"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except Exception:
            return DEFAULT_STRATEGIES.copy()

    def _save_strategies(self, strategies: Dict):
        """Save strategies to disk"""
        atomic_write_json(self.data_file, strategies)
