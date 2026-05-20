"""
Signal Accuracy Tracker - Tracks how accurate past signals were.
Measures hit rate of BUY/SELL signals after configurable time windows.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('memecoin.services.accuracy')


class SignalAccuracyTracker:
    """Tracks and reports signal accuracy over time"""

    def __init__(self):
        self.data_dir = os.path.join(Config.DATA_DIR, 'signals')

    def calculate_accuracy(self, hours_lookback: int = 24) -> Dict[str, Any]:
        """
        Calculate signal accuracy by checking which signals were profitable.
        
        A BUY signal is "accurate" if price went up within the next X hours.
        A SELL/AVOID signal is "accurate" if price went down.
        """
        from .signal_generator import SignalGenerator
        from .price_tracker import PriceTracker

        generator = SignalGenerator()
        tracker = PriceTracker.instance()

        # Get signals from the lookback period
        signals = generator.get_signals(active_only=False, limit=100)
        cutoff = datetime.now() - timedelta(hours=hours_lookback)

        results = {
            "total_signals": 0,
            "evaluated": 0,
            "accurate": 0,
            "inaccurate": 0,
            "accuracy_rate": 0,
            "by_type": {},
            "by_strength": {},
            "window_hours": hours_lookback,
            "evaluated_at": datetime.now().isoformat(),
        }

        for signal in signals:
            try:
                created = datetime.fromisoformat(signal.created_at)
                if created < cutoff:
                    continue
            except Exception:
                continue

            results["total_signals"] += 1

            # Get current price
            try:
                metrics = tracker.get_metrics_by_address(signal.token_address, signal.chain)
                current_price = metrics.get("price_usd", 0)

                if current_price <= 0 or signal.price_at_signal <= 0:
                    continue

                price_change_pct = (current_price - signal.price_at_signal) / signal.price_at_signal * 100

                # Determine if signal was accurate
                is_buy_signal = signal.signal_type.value in [
                    "whale_buy", "smart_money_entry", "pump_detected",
                    "volume_surge", "price_breakout", "holder_surge",
                    "sentiment_spike", "influencer_mention"
                ]
                is_sell_signal = signal.signal_type.value in [
                    "whale_sell", "smart_money_exit", "dump_detected",
                    "rug_risk", "contract_risk", "lp_unlock"
                ]

                if is_buy_signal:
                    accurate = price_change_pct > 0
                elif is_sell_signal:
                    accurate = price_change_pct < 0
                else:
                    continue

                results["evaluated"] += 1
                if accurate:
                    results["accurate"] += 1
                else:
                    results["inaccurate"] += 1

                # Track by type
                sig_type = signal.signal_type.value
                if sig_type not in results["by_type"]:
                    results["by_type"][sig_type] = {"total": 0, "accurate": 0, "avg_price_change": 0, "changes": []}
                results["by_type"][sig_type]["total"] += 1
                if accurate:
                    results["by_type"][sig_type]["accurate"] += 1
                results["by_type"][sig_type]["changes"].append(price_change_pct)

                # Track by strength
                strength = signal.strength.value
                if strength not in results["by_strength"]:
                    results["by_strength"][strength] = {"total": 0, "accurate": 0}
                results["by_strength"][strength]["total"] += 1
                if accurate:
                    results["by_strength"][strength]["accurate"] += 1

            except Exception:
                continue

        # Calculate rates
        if results["evaluated"] > 0:
            results["accuracy_rate"] = results["accurate"] / results["evaluated"] * 100

        for sig_type, data in results["by_type"].items():
            if data["total"] > 0:
                data["accuracy_rate"] = data["accurate"] / data["total"] * 100
                data["avg_price_change"] = sum(data["changes"]) / len(data["changes"]) if data["changes"] else 0
            del data["changes"]  # Remove raw data from response

        for strength, data in results["by_strength"].items():
            if data["total"] > 0:
                data["accuracy_rate"] = data["accurate"] / data["total"] * 100

        return results
