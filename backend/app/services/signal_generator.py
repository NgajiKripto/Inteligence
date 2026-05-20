"""
Signal Generator Service - Generates and manages trading signals
Combines data from multiple sources to produce actionable alerts
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..config import Config
from ..models.signal import Signal, SignalType, SignalStrength
from ..utils.logger import get_logger

logger = get_logger('memecoin.services.signal')


class SignalGenerator:
    """Generates and manages trading signals from multiple data sources"""
    
    def __init__(self):
        self.data_dir = os.path.join(Config.DATA_DIR, 'signals')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_signals(self, signal_type: str = "", min_strength: str = "",
                    chain: str = "all", token_id: str = "",
                    limit: int = 50, active_only: bool = True) -> List[Signal]:
        """Get filtered list of signals"""
        signals = self._load_all_signals()
        
        # Filter
        if active_only:
            signals = [s for s in signals if s.is_active]
        
        if signal_type:
            signals = [s for s in signals if s.signal_type.value == signal_type]
        
        if chain != "all":
            signals = [s for s in signals if s.chain == chain]
        
        if token_id:
            signals = [s for s in signals if s.token_id == token_id]
        
        if min_strength:
            strength_order = ["weak", "moderate", "strong", "very_strong"]
            min_idx = strength_order.index(min_strength) if min_strength in strength_order else 0
            signals = [s for s in signals if strength_order.index(s.strength.value) >= min_idx]
        
        # Sort by creation time (newest first)
        signals.sort(key=lambda s: s.created_at, reverse=True)
        
        return signals[:limit]
    
    def generate_signal(self, signal_type: SignalType, token_id: str = "",
                        token_symbol: str = "", token_address: str = "",
                        chain: str = "solana", title: str = "",
                        description: str = "", confidence: float = 0.5,
                        data_points: Dict = None, source: str = "",
                        price_at_signal: float = 0) -> Signal:
        """Create and save a new signal"""
        
        # Determine strength from confidence
        if confidence >= 0.85:
            strength = SignalStrength.VERY_STRONG
        elif confidence >= 0.6:
            strength = SignalStrength.STRONG
        elif confidence >= 0.3:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        signal = Signal(
            token_id=token_id,
            token_symbol=token_symbol,
            token_address=token_address,
            chain=chain,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            title=title,
            description=description,
            data_points=data_points or {},
            source=source,
            price_at_signal=price_at_signal,
        )
        
        # Generate action suggestion
        signal.action_suggestion = self._generate_suggestion(signal)
        
        # Save
        self._save_signal(signal)
        logger.info(f"Signal generated: {signal.signal_id} - {signal.title}")
        
        return signal
    
    def check_and_generate_signals(self, token_id: str) -> List[Signal]:
        """
        Run signal detection for a specific token
        Checks various conditions and generates appropriate signals
        """
        from .token_scanner import TokenScanner
        from .price_tracker import PriceTracker
        
        scanner = TokenScanner()
        tracker = PriceTracker.instance()
        
        token = scanner.get_token(token_id)
        if not token:
            return []
        
        metrics = tracker.get_metrics_by_address(token.contract_address, token.chain)
        buy_sell = tracker.get_buy_sell_ratio(token.contract_address, token.chain)
        
        generated = []
        
        # Check for volume surge
        volume_24h = metrics.get("volume", {}).get("24h", 0)
        volume_1h = metrics.get("volume", {}).get("1h", 0)
        
        if volume_1h > 0 and volume_24h > 0:
            hourly_avg = volume_24h / 24
            if volume_1h > hourly_avg * 5:
                sig = self.generate_signal(
                    signal_type=SignalType.VOLUME_SURGE,
                    token_id=token_id,
                    token_symbol=token.symbol,
                    token_address=token.contract_address,
                    chain=token.chain,
                    title=f"Volume Surge: {token.symbol}",
                    description=f"1h volume (${volume_1h:,.0f}) is {volume_1h/hourly_avg:.1f}x the 24h average",
                    confidence=min(0.9, volume_1h / hourly_avg / 10),
                    data_points={"volume_1h": volume_1h, "avg_hourly": hourly_avg},
                    source="price_tracker",
                    price_at_signal=metrics.get("price_usd", 0)
                )
                generated.append(sig)
        
        # Check for price breakout
        price_change_1h = metrics.get("price_change", {}).get("1h", 0)
        if abs(price_change_1h) > 20:
            sig_type = SignalType.PRICE_BREAKOUT if price_change_1h > 0 else SignalType.DUMP_DETECTED
            sig = self.generate_signal(
                signal_type=sig_type,
                token_id=token_id,
                token_symbol=token.symbol,
                token_address=token.contract_address,
                chain=token.chain,
                title=f"{'Breakout' if price_change_1h > 0 else 'Dump'}: {token.symbol} {price_change_1h:+.1f}%",
                description=f"Price moved {price_change_1h:+.1f}% in the last hour",
                confidence=min(0.9, abs(price_change_1h) / 50),
                data_points={"price_change_1h": price_change_1h},
                source="price_tracker",
                price_at_signal=metrics.get("price_usd", 0)
            )
            generated.append(sig)
        
        # Check buy/sell pressure
        sell_ratio = buy_sell.get("sell_ratio", 0.5)
        if sell_ratio > 0.8:
            sig = self.generate_signal(
                signal_type=SignalType.DUMP_DETECTED,
                token_id=token_id,
                token_symbol=token.symbol,
                token_address=token.contract_address,
                chain=token.chain,
                title=f"Heavy Selling: {token.symbol}",
                description=f"Sell ratio is {sell_ratio*100:.0f}% - heavy distribution",
                confidence=sell_ratio - 0.3,
                data_points=buy_sell,
                source="price_tracker",
                price_at_signal=metrics.get("price_usd", 0)
            )
            generated.append(sig)
        elif sell_ratio < 0.25:
            sig = self.generate_signal(
                signal_type=SignalType.PUMP_DETECTED,
                token_id=token_id,
                token_symbol=token.symbol,
                token_address=token.contract_address,
                chain=token.chain,
                title=f"Heavy Buying: {token.symbol}",
                description=f"Buy ratio is {(1-sell_ratio)*100:.0f}% - strong accumulation",
                confidence=(1 - sell_ratio) - 0.3,
                data_points=buy_sell,
                source="price_tracker",
                price_at_signal=metrics.get("price_usd", 0)
            )
            generated.append(sig)
        
        return generated
    
    def _generate_suggestion(self, signal: Signal) -> str:
        """Generate human-readable action suggestion"""
        if signal.signal_type in [SignalType.WHALE_BUY, SignalType.SMART_MONEY_ENTRY, SignalType.PUMP_DETECTED]:
            return "Consider entry. Set stop-loss below recent support."
        elif signal.signal_type in [SignalType.WHALE_SELL, SignalType.SMART_MONEY_EXIT, SignalType.DUMP_DETECTED]:
            return "Consider taking profits or tightening stop-loss."
        elif signal.signal_type == SignalType.RUG_RISK:
            return "AVOID. High probability of rug pull."
        elif signal.signal_type == SignalType.VOLUME_SURGE:
            return "Monitor closely. Volume surge often precedes big moves."
        elif signal.signal_type == SignalType.PRICE_BREAKOUT:
            return "Breakout confirmed. Consider entry on pullback."
        elif signal.signal_type == SignalType.SENTIMENT_SPIKE:
            return "Social hype detected. Exercise caution - could be pump & dump."
        else:
            return "Monitor and assess based on other indicators."
    
    # === Storage Methods ===
    
    def _save_signal(self, signal: Signal):
        """Save signal to disk atomically"""
        from ..utils import atomic_write_json
        path = os.path.join(self.data_dir, f"{signal.signal_id}.json")
        atomic_write_json(path, signal.to_dict())
    
    def _load_all_signals(self) -> List[Signal]:
        """Load all saved signals"""
        signals = []
        if not os.path.exists(self.data_dir):
            return signals
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                path = os.path.join(self.data_dir, filename)
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    signals.append(Signal.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to load signal {filename}: {e}")
        
        return signals
