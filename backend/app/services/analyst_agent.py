"""
Analyst Agent - Conversational AI agent for memecoin trading questions
Has access to all analysis tools and can answer questions about tokens
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('memecoin.services.analyst')


SYSTEM_PROMPT = """You are an expert memecoin trading analyst AI assistant. You help traders analyze memecoins on Solana, Ethereum, and BSC.

Your capabilities:
1. On-chain contract analysis (rug-pull detection, honeypot checks)
2. Social sentiment analysis (Twitter, Telegram, Reddit)
3. Whale and smart money tracking
4. Price and volume analysis
5. Multi-agent trading simulations
6. Risk assessment and scoring

Guidelines:
- Be direct and data-driven in your analysis
- Always mention risks prominently - never downplay rug-pull indicators
- If a token looks dangerous, say so clearly with "⚠️ HIGH RISK" or "🚨 AVOID"
- Provide specific, actionable advice
- Use $ amounts and percentages when discussing metrics
- Mention relevant on-chain data (mint authority, LP lock, holder concentration)
- If you don't have enough data, say so and suggest what to check

Format your responses clearly with:
- Key metrics at the top
- Risk assessment
- Action suggestion
- Caveats and disclaimers

Always remind users that memecoin trading is extremely risky and they should never invest more than they can afford to lose."""


class AnalystAgent:
    """Conversational AI analyst for memecoin trading"""
    
    def __init__(self):
        self.llm = LLMClient()
    
    def chat(self, message: str, session_id: str = "",
             token_address: str = "", chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Chat with the analyst agent
        
        The agent can use context from:
        - Active analysis sessions
        - Token watchlist data
        - Real-time market data
        """
        context = self._build_context(session_id, token_address)
        
        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}
        ]
        
        # Add chat history
        if chat_history:
            for msg in chat_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.llm.chat_messages(messages, temperature=0.5)
            
            return {
                "response": response,
                "context_used": bool(context),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analyst chat failed: {e}")
            return {
                "response": f"I encountered an error processing your request: {str(e)}. Please try again.",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _build_context(self, session_id: str, token_address: str) -> str:
        """Build context from available data"""
        context_parts = []
        
        # Load session data if available
        if session_id:
            try:
                from .analysis_engine import AnalysisEngine
                engine = AnalysisEngine()
                session = engine.get_session(session_id)
                
                if session:
                    context_parts.append(f"""ACTIVE ANALYSIS SESSION:
- Token: {session.token_symbol} ({session.token_address})
- Chain: {session.chain}
- Status: {session.status.value}
- On-chain Safety: {session.on_chain_score}/100
- Social Score: {session.social_score}/100
- Liquidity Score: {session.liquidity_score}/100
- Risk Score: {session.risk_score}
- Recommendation: {session.recommendation}
- Key Findings: {json.dumps(session.key_findings)}
- Risk Factors: {json.dumps(session.risk_factors)}""")
                    
                    if session.simulation:
                        sim = session.simulation
                        context_parts.append(f"""
SIMULATION RESULTS:
- Agents: {sim.total_agents}, Rounds: {sim.rounds_completed}
- Buy: {sim.buy_percentage}%, Sell: {sim.sell_percentage}%, Hold: {sim.hold_percentage}%
- Consensus: {sim.consensus_action} (strength: {sim.consensus_strength})
- Predicted 24h: ${sim.predicted_price_24h}""")
            except Exception as e:
                logger.warning(f"Failed to load session context: {e}")
        
        # Load token data if address provided
        if token_address:
            try:
                from .price_tracker import PriceTracker
                tracker = PriceTracker()
                metrics = tracker.get_metrics_by_address(token_address)
                
                if not metrics.get("error"):
                    context_parts.append(f"""LIVE MARKET DATA:
- Price: ${metrics.get('price_usd', 0)}
- 24h Change: {metrics.get('price_change', {}).get('24h', 0)}%
- Volume 24h: ${metrics.get('volume', {}).get('24h', 0):,.0f}
- Liquidity: ${metrics.get('liquidity_usd', 0):,.0f}
- Market Cap: ${metrics.get('market_cap', 0):,.0f}""")
            except Exception as e:
                logger.warning(f"Failed to load token context: {e}")
        
        if context_parts:
            return "\n\nCURRENT CONTEXT:\n" + "\n\n".join(context_parts)
        
        return ""
