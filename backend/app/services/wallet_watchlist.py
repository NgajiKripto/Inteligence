"""
Wallet Watchlist - Track specific wallets and detect overlap with token holders.
Inspired by Charon's saved wallet exposure feature.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..config import Config
from ..utils.logger import get_logger
from ..utils import atomic_write_json

logger = get_logger('memecoin.services.wallets')


class WalletWatchlist:
    """
    Manages a watchlist of wallets (smart money, KOLs, whales).
    Cross-references with token holder lists to detect overlap.
    """

    def __init__(self):
        self.data_file = os.path.join(Config.DATA_DIR, 'wallet_watchlist.json')
        self._ensure_file()

    def add_wallet(self, address: str, label: str, tags: List[str] = None) -> Dict:
        """Add a wallet to the watchlist"""
        wallets = self._load()

        if address in wallets:
            return {"error": f"Wallet {address[:8]}... already tracked as '{wallets[address]['label']}'"}

        wallets[address] = {
            "address": address,
            "label": label,
            "tags": tags or ["smart_money"],
            "added_at": datetime.now().isoformat(),
        }

        self._save(wallets)
        return {"success": True, "wallet": wallets[address]}

    def remove_wallet(self, address: str) -> bool:
        """Remove a wallet from the watchlist"""
        wallets = self._load()
        if address in wallets:
            del wallets[address]
            self._save(wallets)
            return True
        return False

    def list_wallets(self) -> List[Dict]:
        """List all tracked wallets"""
        wallets = self._load()
        return list(wallets.values())

    def check_holder_overlap(self, token_holders: List[str]) -> Dict[str, Any]:
        """
        Check if any tracked wallets appear in a token's holder list.
        
        Args:
            token_holders: list of holder wallet addresses
            
        Returns:
            - overlap_count: number of tracked wallets holding this token
            - wallets: details of matching wallets
            - signal_strength: how strong the smart money signal is
        """
        wallets = self._load()
        if not wallets or not token_holders:
            return {
                "overlap_count": 0,
                "tracked_total": len(wallets),
                "wallets": [],
                "signal_strength": "none",
            }

        holder_set = set(token_holders)
        matches = []

        for address, info in wallets.items():
            if address in holder_set:
                matches.append(info)

        # Signal strength
        count = len(matches)
        if count >= 5:
            strength = "very_strong"
        elif count >= 3:
            strength = "strong"
        elif count >= 2:
            strength = "moderate"
        elif count >= 1:
            strength = "weak"
        else:
            strength = "none"

        return {
            "overlap_count": count,
            "tracked_total": len(wallets),
            "wallets": matches,
            "signal_strength": strength,
        }

    def _ensure_file(self):
        """Ensure data file exists"""
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            atomic_write_json(self.data_file, {})

    def _load(self) -> Dict[str, Dict]:
        """Load wallets from disk"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, wallets: Dict):
        """Save wallets to disk"""
        atomic_write_json(self.data_file, wallets)
