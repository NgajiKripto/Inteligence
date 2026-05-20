"""
On-Chain Analyzer Service - Analyzes smart contract safety and holder distribution
Checks for rug-pull indicators, honeypot risks, and whale concentration
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import requests

from ..config import Config
from ..utils.logger import get_logger
from ..utils import redact_url

logger = get_logger('memecoin.services.onchain')


class OnChainAnalyzer:
    """Analyzes on-chain data for memecoin safety assessment"""
    
    def __init__(self):
        self.solana_rpc = Config.SOLANA_RPC_URL
        self.helius_key = Config.HELIUS_API_KEY
    
    @property
    def _helius_rpc_url(self) -> str:
        """Helius RPC URL (keep key out of direct string interpolation in business logic)"""
        return f"https://mainnet.helius-rpc.com/?api-key={self.helius_key}"
    
    @property
    def _helius_api_url(self) -> str:
        """Helius REST API URL"""
        return f"https://api.helius.xyz/v0/token-metadata?api-key={self.helius_key}"
    
    def get_holder_analysis(self, token_id: str, top_n: int = 20) -> Dict[str, Any]:
        """
        Analyze token holder distribution
        
        Returns:
            - Top holders with percentage
            - Concentration metrics
            - Insider/dev wallet detection
        """
        from .token_scanner import TokenScanner
        scanner = TokenScanner()
        token = scanner.get_token(token_id)
        
        if not token:
            return {"error": f"Token {token_id} not found"}
        
        return self.analyze_holders(token.contract_address, token.chain, top_n)
    
    def analyze_holders(self, address: str, chain: str = "solana", top_n: int = 20) -> Dict[str, Any]:
        """Analyze holder distribution for a token address"""
        try:
            if chain == "solana" and self.helius_key:
                return self._analyze_solana_holders(address, top_n)
            
            # Fallback: return basic analysis
            return {
                "token_address": address,
                "chain": chain,
                "total_holders": 0,
                "top_holders": [],
                "concentration": {
                    "top5_pct": 0,
                    "top10_pct": 0,
                    "top20_pct": 0,
                },
                "risk_indicators": {
                    "high_concentration": False,
                    "single_wallet_dominant": False,
                    "dev_wallet_large": False,
                },
                "note": "Full holder analysis requires Helius API key",
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Holder analysis failed: {e}")
            return {"error": str(e)}
    
    def analyze_contract_safety(self, address: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Comprehensive contract safety analysis
        
        Checks:
        - Mint authority (can dev mint more tokens?)
        - Freeze authority (can dev freeze wallets?)
        - LP lock status
        - Honeypot indicators
        - Tax rates
        """
        try:
            safety = {
                "token_address": address,
                "chain": chain,
                "checks": {},
                "overall_safety_score": 0,  # 0-100
                "risk_level": "unknown",
                "warnings": [],
                "updated_at": datetime.now().isoformat()
            }
            
            if chain == "solana":
                safety = self._check_solana_contract(address, safety)
            elif chain == "ethereum" or chain == "bsc":
                safety = self._check_evm_contract(address, chain, safety)
            
            # Calculate safety score
            checks = safety["checks"]
            score = 100
            warnings = []
            
            # Only penalize if check was actually performed (not None)
            mint_disabled = checks.get("mint_disabled")
            if mint_disabled is False:  # Explicitly False, not None
                score -= 30
                warnings.append("Mint authority is NOT disabled - dev can create new tokens")
            
            freeze_disabled = checks.get("freeze_disabled")
            if freeze_disabled is False:  # Explicitly False, not None
                score -= 20
                warnings.append("Freeze authority is NOT disabled - dev can freeze wallets")
            
            if checks.get("has_blacklist") is True:
                score -= 15
                warnings.append("Contract has blacklist function")
            
            lp_locked = checks.get("lp_locked")
            if lp_locked is False:  # Explicitly False, not None
                score -= 25
                warnings.append("Liquidity pool is NOT locked")
            
            if checks.get("honeypot_risk") is True:
                score -= 40
                warnings.append("HONEYPOT RISK DETECTED - selling may be restricted")
            
            buy_tax = checks.get("tax_buy", 0) or 0
            sell_tax = checks.get("tax_sell", 0) or 0
            if sell_tax > 10:
                score -= 20
                warnings.append(f"High sell tax: {sell_tax}%")
            elif sell_tax > 5:
                score -= 10
                warnings.append(f"Moderate sell tax: {sell_tax}%")
            
            safety["overall_safety_score"] = max(0, score)
            safety["warnings"] = warnings
            
            if score >= 80:
                safety["risk_level"] = "low"
            elif score >= 60:
                safety["risk_level"] = "medium"
            elif score >= 40:
                safety["risk_level"] = "high"
            else:
                safety["risk_level"] = "critical"
            
            return safety
            
        except Exception as e:
            logger.error(f"Contract safety check failed: {e}")
            return {"error": str(e), "token_address": address}
    
    def get_token_metadata(self, address: str, chain: str = "solana") -> Dict[str, Any]:
        """Get token metadata (name, symbol, supply, decimals)"""
        try:
            if chain == "solana" and self.helius_key:
                return self._get_solana_metadata(address)
            return {"address": address, "chain": chain}
        except Exception as e:
            logger.error(f"Get metadata failed: {e}")
            return {"error": str(e)}
    
    # === Solana-specific methods ===
    
    def _analyze_solana_holders(self, address: str, top_n: int) -> Dict[str, Any]:
        """Analyze Solana token holders via Helius"""
        try:
            rpc_url = self._helius_rpc_url
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [address]
            }
            
            resp = requests.post(rpc_url, json=payload, timeout=15)
            if resp.status_code != 200:
                return {"error": "Helius RPC call failed"}
            
            result = resp.json().get("result", {})
            accounts = result.get("value", [])
            
            # Calculate totals and percentages
            total_supply = sum(float(a.get("uiAmount", 0) or 0) for a in accounts)
            
            top_holders = []
            for i, account in enumerate(accounts[:top_n]):
                amount = float(account.get("uiAmount", 0) or 0)
                pct = (amount / total_supply * 100) if total_supply > 0 else 0
                top_holders.append({
                    "rank": i + 1,
                    "address": account.get("address", ""),
                    "amount": amount,
                    "percentage": round(pct, 2),
                })
            
            # Concentration metrics
            top5_pct = sum(h["percentage"] for h in top_holders[:5])
            top10_pct = sum(h["percentage"] for h in top_holders[:10])
            top20_pct = sum(h["percentage"] for h in top_holders[:20])
            
            return {
                "token_address": address,
                "chain": "solana",
                "total_holders_sampled": len(accounts),
                "top_holders": top_holders,
                "concentration": {
                    "top5_pct": round(top5_pct, 2),
                    "top10_pct": round(top10_pct, 2),
                    "top20_pct": round(top20_pct, 2),
                },
                "risk_indicators": {
                    "high_concentration": top10_pct > 50,
                    "single_wallet_dominant": top_holders[0]["percentage"] > 20 if top_holders else False,
                    "dev_wallet_large": top_holders[0]["percentage"] > 30 if top_holders else False,
                },
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Solana holder analysis failed: {redact_url(str(e))}")
            return {"error": "Solana holder analysis failed"}
    
    def _check_solana_contract(self, address: str, safety: Dict) -> Dict:
        """Check Solana token contract safety"""
        try:
            if not self.helius_key:
                safety["checks"] = {
                    "mint_disabled": None,
                    "freeze_disabled": None,
                    "lp_locked": None,
                    "honeypot_risk": False,
                    "note": "Helius API key required for full analysis"
                }
                return safety
            
            rpc_url = self._helius_rpc_url
            
            # Get mint info
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [address, {"encoding": "jsonParsed"}]
            }
            
            resp = requests.post(rpc_url, json=payload, timeout=15)
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                value = result.get("value", {})
                parsed = value.get("data", {}).get("parsed", {})
                info = parsed.get("info", {})
                
                mint_authority = info.get("mintAuthority")
                freeze_authority = info.get("freezeAuthority")
                
                safety["checks"] = {
                    "mint_disabled": mint_authority is None,
                    "freeze_disabled": freeze_authority is None,
                    "mint_authority": mint_authority or "None (disabled)",
                    "freeze_authority": freeze_authority or "None (disabled)",
                    "supply": info.get("supply", "0"),
                    "decimals": info.get("decimals", 0),
                    "lp_locked": None,  # Requires LP analysis
                    "honeypot_risk": False,
                    "tax_buy": 0,
                    "tax_sell": 0,
                }
            
            return safety
            
        except Exception as e:
            logger.error(f"Solana contract check failed: {redact_url(str(e))}")
            safety["checks"] = {"error": "Contract check failed"}
            return safety
    
    def _check_evm_contract(self, address: str, chain: str, safety: Dict) -> Dict:
        """Check EVM (Ethereum/BSC) contract safety"""
        # Placeholder for EVM contract analysis
        safety["checks"] = {
            "mint_disabled": None,
            "freeze_disabled": None,
            "has_blacklist": None,
            "lp_locked": None,
            "honeypot_risk": None,
            "tax_buy": 0,
            "tax_sell": 0,
            "note": "EVM contract analysis - implementation pending"
        }
        return safety
    
    def _get_solana_metadata(self, address: str) -> Dict[str, Any]:
        """Get Solana token metadata via Helius"""
        try:
            url = self._helius_api_url
            resp = requests.post(url, json={"mintAccounts": [address]}, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    meta = data[0]
                    return {
                        "address": address,
                        "name": meta.get("onChainAccountInfo", {}).get("metadata", {}).get("data", {}).get("name", ""),
                        "symbol": meta.get("onChainAccountInfo", {}).get("metadata", {}).get("data", {}).get("symbol", ""),
                        "uri": meta.get("onChainAccountInfo", {}).get("metadata", {}).get("data", {}).get("uri", ""),
                    }
            
            return {"address": address}
            
        except Exception as e:
            logger.error(f"Get Solana metadata failed: {e}")
            return {"address": address, "error": str(e)}
