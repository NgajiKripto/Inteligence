"""
Risk Assessor Service - Comprehensive risk scoring for memecoins
Combines on-chain, social, and market data to produce risk ratings
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from ..config import Config
from ..models.token import TokenRiskLevel
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('memecoin.services.risk')


class RiskAssessor:
    """Assesses rug-pull and trading risk for memecoin tokens"""
    
    def __init__(self):
        self.llm = LLMClient()
    
    def assess_token(self, token_id: str) -> Dict[str, Any]:
        """
        Full risk assessment for a tracked token
        Combines multiple data sources into a composite risk score
        """
        from .token_scanner import TokenScanner
        from .onchain_analyzer import OnChainAnalyzer
        from .price_tracker import PriceTracker
        
        scanner = TokenScanner()
        token = scanner.get_token(token_id)
        
        if not token:
            return {"error": f"Token {token_id} not found"}
        
        # Gather data
        onchain = OnChainAnalyzer()
        tracker = PriceTracker.instance()
        
        contract_safety = onchain.analyze_contract_safety(token.contract_address, token.chain)
        holder_data = onchain.analyze_holders(token.contract_address, token.chain)
        buy_sell = tracker.get_buy_sell_ratio(token.contract_address, token.chain)
        
        # Calculate composite risk score
        risk_result = self._calculate_risk_score(
            contract_safety=contract_safety,
            holder_data=holder_data,
            buy_sell=buy_sell,
            metrics=token.metrics.model_dump() if token.metrics else {}
        )
        
        # Update token with risk data
        token.risk_score = risk_result["risk_score"]
        token.risk_level = TokenRiskLevel(risk_result["risk_level"])
        token.risk_factors = risk_result["risk_factors"]
        token.updated_at = datetime.now().isoformat()
        scanner._save_token(token)
        
        return risk_result
    
    def quick_rug_check(self, token_address: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Quick rug-pull risk check without requiring token to be tracked
        Returns immediate safety assessment
        """
        from .onchain_analyzer import OnChainAnalyzer
        from .price_tracker import PriceTracker
        
        onchain = OnChainAnalyzer()
        tracker = PriceTracker.instance()
        
        # Get contract safety
        contract_safety = onchain.analyze_contract_safety(token_address, chain)
        
        # Get holder data
        holder_data = onchain.analyze_holders(token_address, chain)
        
        # Get price metrics
        metrics = tracker.get_metrics_by_address(token_address, chain)
        buy_sell = tracker.get_buy_sell_ratio(token_address, chain)
        
        # Calculate risk
        risk_result = self._calculate_risk_score(
            contract_safety=contract_safety,
            holder_data=holder_data,
            buy_sell=buy_sell,
            metrics=metrics
        )
        
        # Add specific rug indicators
        risk_result["rug_indicators"] = self._check_rug_indicators(
            contract_safety, holder_data, metrics
        )
        
        risk_result["token_address"] = token_address
        risk_result["chain"] = chain
        risk_result["checked_at"] = datetime.now().isoformat()
        
        return risk_result
    
    def _calculate_risk_score(self, contract_safety: Dict, holder_data: Dict,
                              buy_sell: Dict, metrics: Dict) -> Dict[str, Any]:
        """
        Calculate composite risk score from multiple data points
        
        Score: 0.0 (very safe) to 1.0 (extreme risk / likely rug)
        """
        risk_score = 0.0
        risk_factors = []
        safety_factors = []
        
        # === Contract Safety (40% weight) ===
        checks = contract_safety.get("checks", {})
        
        if checks.get("mint_disabled") is False:
            risk_score += 0.15
            risk_factors.append("Mint authority NOT disabled")
        elif checks.get("mint_disabled") is True:
            safety_factors.append("Mint authority disabled")
        
        if checks.get("freeze_disabled") is False:
            risk_score += 0.10
            risk_factors.append("Freeze authority NOT disabled")
        elif checks.get("freeze_disabled") is True:
            safety_factors.append("Freeze authority disabled")
        
        if checks.get("honeypot_risk"):
            risk_score += 0.25
            risk_factors.append("HONEYPOT RISK: Selling may be blocked")
        
        if not checks.get("lp_locked", False) and checks.get("lp_locked") is not None:
            risk_score += 0.12
            risk_factors.append("Liquidity pool NOT locked")
        elif checks.get("lp_locked"):
            safety_factors.append("LP locked")
        
        if checks.get("has_blacklist"):
            risk_score += 0.08
            risk_factors.append("Contract has blacklist function")
        
        sell_tax = checks.get("tax_sell", 0)
        if sell_tax > 15:
            risk_score += 0.15
            risk_factors.append(f"Extremely high sell tax: {sell_tax}%")
        elif sell_tax > 5:
            risk_score += 0.05
            risk_factors.append(f"Elevated sell tax: {sell_tax}%")
        
        # === Holder Concentration (30% weight) ===
        concentration = holder_data.get("concentration", {})
        top10_pct = concentration.get("top10_pct", 0)
        
        if top10_pct > 80:
            risk_score += 0.20
            risk_factors.append(f"Extreme holder concentration: Top 10 hold {top10_pct}%")
        elif top10_pct > 60:
            risk_score += 0.12
            risk_factors.append(f"High holder concentration: Top 10 hold {top10_pct}%")
        elif top10_pct > 40:
            risk_score += 0.05
            risk_factors.append(f"Moderate concentration: Top 10 hold {top10_pct}%")
        else:
            safety_factors.append(f"Good distribution: Top 10 hold {top10_pct}%")
        
        risk_indicators = holder_data.get("risk_indicators", {})
        if risk_indicators.get("single_wallet_dominant"):
            risk_score += 0.10
            risk_factors.append("Single wallet holds dominant position")
        
        # === Market Metrics (20% weight) ===
        liquidity = metrics.get("liquidity_usd", 0)
        if isinstance(liquidity, (int, float)):
            if liquidity < 5000:
                risk_score += 0.15
                risk_factors.append(f"Very low liquidity: ${liquidity:,.0f}")
            elif liquidity < 20000:
                risk_score += 0.08
                risk_factors.append(f"Low liquidity: ${liquidity:,.0f}")
            elif liquidity > 100000:
                safety_factors.append(f"Good liquidity: ${liquidity:,.0f}")
        
        # Buy/sell pressure
        sell_ratio = buy_sell.get("sell_ratio", 0.5)
        if sell_ratio > 0.75:
            risk_score += 0.05
            risk_factors.append("Heavy selling pressure")
        
        # === Age Factor (10% weight) ===
        # Newer tokens are generally riskier
        # (Would check deploy date vs now)
        
        # Cap at 1.0
        risk_score = min(1.0, risk_score)
        
        # Determine level
        if risk_score >= Config.RISK_SCORE_CRITICAL:
            risk_level = "critical"
        elif risk_score >= Config.RISK_SCORE_HIGH:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "safety_factors": safety_factors,
            "contract_safety_score": contract_safety.get("overall_safety_score", 0),
            "holder_concentration_top10": top10_pct,
            "liquidity_usd": liquidity if isinstance(liquidity, (int, float)) else 0,
            "sell_pressure": buy_sell.get("pressure", "unknown"),
            "updated_at": datetime.now().isoformat()
        }
    
    def _check_rug_indicators(self, contract_safety: Dict, holder_data: Dict,
                               metrics: Dict) -> List[Dict[str, Any]]:
        """Check for specific rug-pull indicators"""
        indicators = []
        
        checks = contract_safety.get("checks", {})
        
        # Critical indicators
        if checks.get("honeypot_risk"):
            indicators.append({
                "indicator": "honeypot",
                "severity": "critical",
                "description": "Token may be a honeypot - selling could be blocked"
            })
        
        if checks.get("mint_disabled") is False:
            indicators.append({
                "indicator": "unlimited_mint",
                "severity": "high",
                "description": "Developer can mint unlimited tokens, diluting value"
            })
        
        if not checks.get("lp_locked", True) and checks.get("lp_locked") is not None:
            indicators.append({
                "indicator": "unlocked_lp",
                "severity": "high",
                "description": "Liquidity pool not locked - dev can pull liquidity"
            })
        
        # Concentration
        concentration = holder_data.get("concentration", {})
        if concentration.get("top5_pct", 0) > 70:
            indicators.append({
                "indicator": "insider_concentration",
                "severity": "high",
                "description": f"Top 5 wallets hold {concentration['top5_pct']}% of supply"
            })
        
        # Low liquidity
        liquidity = metrics.get("liquidity_usd", 0)
        if isinstance(liquidity, (int, float)) and 0 < liquidity < 5000:
            indicators.append({
                "indicator": "micro_liquidity",
                "severity": "medium",
                "description": f"Extremely low liquidity (${liquidity:,.0f}) - high slippage risk"
            })
        
        return indicators
