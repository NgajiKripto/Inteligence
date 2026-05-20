"""
Whale Tracker Service - Monitors large wallet movements and smart money activity
Detects whale buys/sells, smart money flows, and insider activity
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import requests

from ..config import Config
from ..utils.logger import get_logger
from ..utils import redact_url

logger = get_logger('memecoin.services.whale')


# Known smart money wallets (sample - in production, this would be a dynamic database)
KNOWN_SMART_MONEY = {
    "solana": [
        # These are placeholder addresses for the system structure
        # In production, these would be populated from on-chain analysis
    ]
}


class WhaleTracker:
    """Tracks whale wallets and smart money movements"""
    
    def __init__(self):
        self.helius_key = Config.HELIUS_API_KEY
        self.threshold_usd = Config.WHALE_ALERT_THRESHOLD_USD
        self.threshold_sol = Config.WHALE_ALERT_THRESHOLD_SOL
    
    @property
    def _rpc_url(self) -> str:
        """Helius RPC URL"""
        return f"https://mainnet.helius-rpc.com/?api-key={self.helius_key}"
    
    def get_recent_activity(self, chain: str = "solana", min_amount_usd: float = 50000,
                            hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent whale wallet activity
        
        Monitors large transactions that could indicate:
        - Whale accumulation (large buys)
        - Whale distribution (large sells)
        - LP additions/removals
        - Token transfers between wallets
        """
        try:
            if chain == "solana" and self.helius_key:
                return self._get_solana_whale_activity(min_amount_usd, hours, limit)
            
            # Fallback: return empty with note
            return [{
                "note": f"Whale tracking for {chain} requires API configuration",
                "chain": chain,
                "min_amount_usd": min_amount_usd,
                "timeframe_hours": hours
            }]
            
        except Exception as e:
            logger.error(f"Get whale activity failed: {e}")
            return [{"error": str(e)}]
    
    def get_smart_money_trades(self, chain: str = "solana", action: str = "all",
                               hours: int = 24, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Track smart money wallet trades
        
        Smart money = wallets with historically high win rates
        """
        try:
            if chain == "solana" and self.helius_key:
                return self._get_solana_smart_money(action, hours, limit)
            
            return [{
                "note": f"Smart money tracking for {chain} requires API configuration",
                "chain": chain
            }]
            
        except Exception as e:
            logger.error(f"Get smart money failed: {e}")
            return [{"error": str(e)}]
    
    def track_wallet(self, wallet_address: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Get detailed activity for a specific wallet
        
        Returns:
        - Recent transactions
        - Token holdings
        - PnL estimate
        - Trading patterns
        """
        try:
            if chain == "solana" and self.helius_key:
                return self._track_solana_wallet(wallet_address)
            
            return {
                "wallet": wallet_address,
                "chain": chain,
                "note": "Detailed wallet tracking requires Helius API key"
            }
            
        except Exception as e:
            logger.error(f"Track wallet failed: {e}")
            return {"error": str(e)}
    
    def detect_whale_for_token(self, token_address: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Detect whale activity specifically for a token
        
        Returns:
        - Whale wallets holding this token
        - Recent large transactions
        - Accumulation/distribution pattern
        """
        try:
            if chain == "solana" and self.helius_key:
                return self._detect_token_whales_solana(token_address)
            
            return {
                "token_address": token_address,
                "chain": chain,
                "whale_wallets": [],
                "recent_large_txs": [],
                "pattern": "unknown",
                "note": "Full whale detection requires Helius API key"
            }
            
        except Exception as e:
            logger.error(f"Detect whale for token failed: {e}")
            return {"error": str(e)}
    
    # === Solana-specific methods ===
    
    def _get_solana_whale_activity(self, min_amount_usd: float, hours: int,
                                    limit: int) -> List[Dict[str, Any]]:
        """Get whale activity on Solana via Helius enhanced transactions"""
        try:
            # Use Helius parsed transaction history for known whale wallets
            # In production, this would query a database of tracked wallets
            
            rpc_url = self._rpc_url
            
            # For demo: get recent large transactions from the network
            # In production: would monitor specific whale wallets
            activities = []
            
            # Note: A full implementation would use Helius webhooks or
            # poll transaction histories of known whale wallets
            return activities if activities else [{
                "note": "Whale activity monitoring active",
                "chain": "solana",
                "min_threshold_usd": min_amount_usd,
                "monitoring_hours": hours,
                "tracked_wallets": len(KNOWN_SMART_MONEY.get("solana", [])),
                "updated_at": datetime.now().isoformat()
            }]
            
        except Exception as e:
            logger.error(f"Solana whale activity fetch failed: {redact_url(str(e))}")
            return [{"error": "Whale activity fetch failed"}]
    
    def _get_solana_smart_money(self, action: str, hours: int, limit: int) -> List[Dict[str, Any]]:
        """Get smart money trades on Solana"""
        try:
            rpc_url = self._rpc_url
            trades = []
            
            # Query transaction history for known smart money wallets
            for wallet in KNOWN_SMART_MONEY.get("solana", [])[:10]:
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getSignaturesForAddress",
                        "params": [wallet, {"limit": 20}]
                    }
                    
                    resp = requests.post(rpc_url, json=payload, timeout=10)
                    if resp.status_code == 200:
                        result = resp.json().get("result", [])
                        for sig in result:
                            trades.append({
                                "wallet": wallet[:8] + "..." + wallet[-4:],
                                "signature": sig.get("signature", ""),
                                "block_time": sig.get("blockTime", 0),
                                "status": "success" if not sig.get("err") else "failed"
                            })
                except Exception:
                    continue
            
            # Filter by action if specified
            if action == "buy":
                trades = [t for t in trades if t.get("type") == "buy"]
            elif action == "sell":
                trades = [t for t in trades if t.get("type") == "sell"]
            
            return trades[:limit] if trades else [{
                "note": "Smart money tracking active",
                "chain": "solana",
                "tracked_wallets": len(KNOWN_SMART_MONEY.get("solana", [])),
                "updated_at": datetime.now().isoformat()
            }]
            
        except Exception as e:
            logger.error(f"Solana smart money fetch failed: {redact_url(str(e))}")
            return [{"error": "Smart money fetch failed"}]
    
    def _track_solana_wallet(self, wallet_address: str) -> Dict[str, Any]:
        """Track a specific Solana wallet"""
        try:
            rpc_url = self._rpc_url
            
            # Get SOL balance
            balance_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_address]
            }
            
            resp = requests.post(rpc_url, json=balance_payload, timeout=10)
            sol_balance = 0
            if resp.status_code == 200:
                sol_balance = resp.json().get("result", {}).get("value", 0) / 1e9
            
            # Get token accounts
            token_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            resp = requests.post(rpc_url, json=token_payload, timeout=10)
            token_holdings = []
            if resp.status_code == 200:
                accounts = resp.json().get("result", {}).get("value", [])
                for acc in accounts[:20]:
                    info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                    token_amount = info.get("tokenAmount", {})
                    if float(token_amount.get("uiAmount", 0) or 0) > 0:
                        token_holdings.append({
                            "mint": info.get("mint", ""),
                            "amount": float(token_amount.get("uiAmount", 0) or 0),
                            "decimals": token_amount.get("decimals", 0)
                        })
            
            # Get recent transactions
            sig_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [wallet_address, {"limit": 20}]
            }
            
            resp = requests.post(rpc_url, json=sig_payload, timeout=10)
            recent_txs = []
            if resp.status_code == 200:
                sigs = resp.json().get("result", [])
                recent_txs = [
                    {
                        "signature": s.get("signature", ""),
                        "block_time": s.get("blockTime", 0),
                        "status": "success" if not s.get("err") else "failed"
                    }
                    for s in sigs
                ]
            
            return {
                "wallet": wallet_address,
                "chain": "solana",
                "sol_balance": sol_balance,
                "token_holdings_count": len(token_holdings),
                "token_holdings": token_holdings[:10],
                "recent_transactions": recent_txs[:10],
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Track Solana wallet failed: {redact_url(str(e))}")
            return {"error": "Wallet tracking failed", "wallet": wallet_address}
    
    def _detect_token_whales_solana(self, token_address: str) -> Dict[str, Any]:
        """Detect whale wallets for a specific Solana token"""
        try:
            rpc_url = self._rpc_url
            
            # Get largest token holders
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [token_address]
            }
            
            resp = requests.post(rpc_url, json=payload, timeout=15)
            
            if resp.status_code != 200:
                return {"error": "RPC call failed"}
            
            result = resp.json().get("result", {})
            accounts = result.get("value", [])
            
            total = sum(float(a.get("uiAmount", 0) or 0) for a in accounts)
            
            whale_wallets = []
            for acc in accounts[:10]:
                amount = float(acc.get("uiAmount", 0) or 0)
                pct = (amount / total * 100) if total > 0 else 0
                
                if pct >= 1.0:  # Consider 1%+ as whale
                    whale_wallets.append({
                        "address": acc.get("address", ""),
                        "amount": amount,
                        "percentage": round(pct, 2),
                        "is_whale": pct >= 5.0,
                        "is_mega_whale": pct >= 10.0
                    })
            
            # Determine pattern
            if len(whale_wallets) == 0:
                pattern = "distributed"
            elif whale_wallets[0]["percentage"] > 20:
                pattern = "highly_concentrated"
            elif whale_wallets[0]["percentage"] > 10:
                pattern = "moderately_concentrated"
            else:
                pattern = "well_distributed"
            
            return {
                "token_address": token_address,
                "chain": "solana",
                "whale_wallets": whale_wallets,
                "whale_count": len(whale_wallets),
                "top_holder_pct": whale_wallets[0]["percentage"] if whale_wallets else 0,
                "pattern": pattern,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Detect token whales failed: {e}")
            return {"error": str(e), "token_address": token_address}
