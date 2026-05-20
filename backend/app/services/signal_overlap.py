"""
Signal Overlap Scorer - Multi-source signal overlap detection.
Inspired by Charon's requirement of 2+ independent signal sources.
Tokens appearing in multiple data feeds simultaneously get higher priority.

State is persisted to disk so overlap data survives restarts.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List

from ..config import Config
from ..utils.logger import get_logger
from ..utils import atomic_write_json

logger = get_logger('memecoin.services.overlap')


class SignalOverlapScorer:
    """
    Detects when a token appears in multiple independent signal sources.
    Higher overlap = higher confidence the signal is real.
    
    Signal sources:
    1. DexScreener trending
    2. Whale buy activity
    3. Social media spike (Twitter mentions)
    4. Volume surge
    5. New pair detection
    6. Smart money entry
    7. GMGN trending
    
    State is persisted to disk to survive restarts.
    """

    def __init__(self):
        self._overlap_window_ms = 30 * 60 * 1000  # 30 min window
        self._data_file = os.path.join(Config.DATA_DIR, 'signal_overlap.json')
        self._signal_events: Dict[str, List[Dict]] = self._load_state()

    def record_signal(self, token_address: str, source: str, 
                      data: Dict[str, Any] = None):
        """Record a signal event for overlap detection"""
        if token_address not in self._signal_events:
            self._signal_events[token_address] = []

        self._signal_events[token_address].append({
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "timestamp_ms": int(datetime.now().timestamp() * 1000),
            "data": data or {},
        })

        # Prune old events
        self._prune_events(token_address)
        # Persist to disk
        self._save_state()

    def get_overlap_score(self, token_address: str) -> Dict[str, Any]:
        """
        Calculate overlap score for a token.
        
        Returns:
            - overlap_count: number of unique signal sources
            - overlap_score: 0.0-1.0 normalized score
            - sources: list of source names
            - label: descriptive label
        """
        self._prune_events(token_address)

        events = self._signal_events.get(token_address, [])
        if not events:
            return {
                "overlap_count": 0,
                "overlap_score": 0.0,
                "sources": [],
                "label": "no_signals",
                "token_address": token_address,
            }

        # Unique sources
        unique_sources = list(set(e["source"] for e in events))
        count = len(unique_sources)

        # Score: 1 source = 0.2, 2 = 0.5, 3 = 0.7, 4+ = 0.9+
        if count >= 5:
            score = 1.0
        elif count >= 4:
            score = 0.9
        elif count >= 3:
            score = 0.7
        elif count >= 2:
            score = 0.5
        else:
            score = 0.2

        # Label
        if count >= 4:
            label = "very_strong_overlap"
        elif count >= 3:
            label = "strong_overlap"
        elif count >= 2:
            label = "moderate_overlap"
        else:
            label = "single_source"

        return {
            "overlap_count": count,
            "overlap_score": score,
            "sources": unique_sources,
            "label": label,
            "token_address": token_address,
            "events_in_window": len(events),
        }

    def get_top_overlaps(self, min_sources: int = 2, limit: int = 20) -> List[Dict]:
        """Get tokens with highest signal overlap"""
        # Prune all
        for addr in list(self._signal_events.keys()):
            self._prune_events(addr)
        self._save_state()

        results = []
        for addr in self._signal_events:
            score = self.get_overlap_score(addr)
            if score["overlap_count"] >= min_sources:
                results.append(score)

        results.sort(key=lambda x: x["overlap_score"], reverse=True)
        return results[:limit]

    def check_minimum_overlap(self, token_address: str, min_sources: int = 2) -> bool:
        """Check if token meets minimum overlap requirement for the active strategy"""
        score = self.get_overlap_score(token_address)
        return score["overlap_count"] >= min_sources

    def _prune_events(self, token_address: str):
        """Remove events older than the overlap window"""
        if token_address not in self._signal_events:
            return

        now_ms = int(datetime.now().timestamp() * 1000)
        cutoff = now_ms - self._overlap_window_ms

        self._signal_events[token_address] = [
            e for e in self._signal_events[token_address]
            if e.get("timestamp_ms", 0) > cutoff
        ]

        if not self._signal_events[token_address]:
            del self._signal_events[token_address]

    def _load_state(self) -> Dict[str, List[Dict]]:
        """Load persisted state from disk"""
        if not os.path.exists(self._data_file):
            return {}
        try:
            with open(self._data_file, 'r') as f:
                data = json.load(f)
            return data.get("events", {})
        except Exception:
            return {}

    def _save_state(self):
        """Persist state to disk"""
        try:
            os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
            atomic_write_json(self._data_file, {
                "events": self._signal_events,
                "saved_at": datetime.now().isoformat(),
            })
        except Exception as e:
            logger.warning(f"Failed to persist overlap state: {e}")


# Singleton instance
_overlap_scorer = None

def get_overlap_scorer() -> SignalOverlapScorer:
    """Get singleton overlap scorer instance"""
    global _overlap_scorer
    if _overlap_scorer is None:
        _overlap_scorer = SignalOverlapScorer()
    return _overlap_scorer
