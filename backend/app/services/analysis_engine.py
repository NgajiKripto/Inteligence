"""
Analysis Engine - Orchestrates the full analysis pipeline for a memecoin
Coordinates all services to produce a comprehensive trading report
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..config import Config
from ..models.analysis import AnalysisSession, AnalysisStatus, SimulationResult
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('memecoin.services.engine')


class AnalysisEngine:
    """
    Orchestrates the full memecoin analysis pipeline:
    1. On-chain data collection & contract safety
    2. Price & liquidity metrics
    3. Social sentiment analysis
    4. Whale/smart money tracking
    5. Multi-agent simulation
    6. AI report generation
    """
    
    def __init__(self):
        self.llm = LLMClient()
        self.data_dir = os.path.join(Config.DATA_DIR, 'sessions')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def create_session(self, token_address: str, chain: str = "solana",
                       analysis_depth: str = "standard", simulate: bool = True,
                       agent_count: int = 50) -> AnalysisSession:
        """Create a new analysis session"""
        session = AnalysisSession(
            token_address=token_address,
            chain=chain,
            status=AnalysisStatus.CREATED,
        )
        
        # Store config in session
        session.current_step = "Session created"
        self._save_session(session)
        
        return session
    
    def run_full_analysis(self, session_id: str):
        """Run the complete analysis pipeline"""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return
        
        try:
            # Step 1: On-chain analysis
            session.status = AnalysisStatus.ANALYZING_ONCHAIN
            session.current_step = "Analyzing smart contract and on-chain data..."
            session.progress = 10
            self._save_session(session)
            
            onchain_data = self._analyze_onchain(session.token_address, session.chain)
            session.on_chain_score = onchain_data.get("overall_safety_score", 0)
            session.progress = 25
            self._save_session(session)
            
            # Step 2: Price & market data
            session.current_step = "Fetching price and market metrics..."
            session.progress = 30
            self._save_session(session)
            
            market_data = self._analyze_market(session.token_address, session.chain)
            session.liquidity_score = self._calculate_liquidity_score(market_data)
            session.progress = 40
            self._save_session(session)
            
            # Step 3: Social sentiment
            session.status = AnalysisStatus.ANALYZING_SOCIAL
            session.current_step = "Analyzing social media sentiment..."
            session.progress = 45
            self._save_session(session)
            
            social_data = self._analyze_social(session.token_symbol or "unknown", session.token_address)
            session.social_score = social_data.get("trending_score", 0) * 100
            session.progress = 60
            self._save_session(session)
            
            # Step 4: Whale tracking
            session.current_step = "Tracking whale and smart money activity..."
            session.progress = 65
            self._save_session(session)
            
            whale_data = self._analyze_whales(session.token_address, session.chain)
            session.progress = 75
            self._save_session(session)
            
            # Step 5: Multi-agent simulation
            session.status = AnalysisStatus.RUNNING_SIMULATION
            session.current_step = "Running multi-agent trading simulation..."
            session.progress = 78
            self._save_session(session)
            
            from .simulation_engine import SimulationEngine
            sim_engine = SimulationEngine()
            
            simulation = sim_engine.run_simulation(
                token_address=session.token_address,
                chain=session.chain,
                agent_count=50,
                rounds=8
            )
            session.simulation = simulation
            session.progress = 90
            self._save_session(session)
            
            # Step 6: Generate report
            session.status = AnalysisStatus.GENERATING_REPORT
            session.current_step = "Generating comprehensive analysis report..."
            session.progress = 92
            self._save_session(session)
            
            report = self._generate_report(
                session=session,
                onchain_data=onchain_data,
                market_data=market_data,
                social_data=social_data,
                whale_data=whale_data,
                simulation=simulation
            )
            
            session.report_markdown = report["markdown"]
            session.report_summary = report["summary"]
            session.recommendation = report["recommendation"]
            session.confidence = report["confidence"]
            session.key_findings = report["key_findings"]
            session.risk_factors = report["risk_factors"]
            session.bullish_factors = report["bullish_factors"]
            session.bearish_factors = report["bearish_factors"]
            session.risk_score = onchain_data.get("risk_score", 0)
            
            # Complete
            session.status = AnalysisStatus.COMPLETED
            session.current_step = "Analysis complete"
            session.progress = 100
            session.completed_at = datetime.now().isoformat()
            self._save_session(session)
            
            logger.info(f"Analysis complete: {session_id}, recommendation={session.recommendation}")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            session.status = AnalysisStatus.FAILED
            session.error = str(e)
            session.current_step = f"Failed: {str(e)}"
            self._save_session(session)
    
    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        """Get an analysis session by ID"""
        path = os.path.join(self.data_dir, f"{session_id}.json")
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        return AnalysisSession.from_dict(data)
    
    def get_history(self, limit: int = 20, status: str = "") -> List[AnalysisSession]:
        """Get analysis session history"""
        sessions = []
        if not os.path.exists(self.data_dir):
            return sessions
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                path = os.path.join(self.data_dir, filename)
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    session = AnalysisSession.from_dict(data)
                    if not status or session.status.value == status:
                        sessions.append(session)
                except Exception:
                    continue
        
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions[:limit]
    
    # === Pipeline Steps ===
    
    def _analyze_onchain(self, address: str, chain: str) -> Dict[str, Any]:
        """Run on-chain analysis"""
        from .onchain_analyzer import OnChainAnalyzer
        from .risk_assessor import RiskAssessor
        
        onchain = OnChainAnalyzer()
        risk = RiskAssessor()
        
        safety = onchain.analyze_contract_safety(address, chain)
        holders = onchain.analyze_holders(address, chain)
        rug_check = risk.quick_rug_check(address, chain)
        
        return {
            "contract_safety": safety,
            "holder_analysis": holders,
            "rug_check": rug_check,
            "overall_safety_score": safety.get("overall_safety_score", 0),
            "risk_score": rug_check.get("risk_score", 0),
            "risk_level": rug_check.get("risk_level", "unknown"),
            "risk_factors": rug_check.get("risk_factors", []),
            "safety_factors": rug_check.get("safety_factors", []),
        }
    
    def _analyze_market(self, address: str, chain: str) -> Dict[str, Any]:
        """Get market metrics"""
        from .price_tracker import PriceTracker
        tracker = PriceTracker.instance()
        
        metrics = tracker.get_metrics_by_address(address, chain)
        buy_sell = tracker.get_buy_sell_ratio(address, chain)
        
        return {
            "metrics": metrics,
            "buy_sell_ratio": buy_sell,
        }
    
    def _analyze_social(self, symbol: str, address: str) -> Dict[str, Any]:
        """Run social sentiment analysis"""
        from .sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        return analyzer.analyze_token_sentiment(symbol=symbol, address=address)
    
    def _analyze_whales(self, address: str, chain: str) -> Dict[str, Any]:
        """Track whale activity"""
        from .whale_tracker import WhaleTracker
        tracker = WhaleTracker()
        
        return tracker.detect_whale_for_token(address, chain)
    
    def _calculate_liquidity_score(self, market_data: Dict) -> float:
        """Calculate liquidity health score (0-100)"""
        metrics = market_data.get("metrics", {})
        liquidity = metrics.get("liquidity_usd", 0)
        
        if not isinstance(liquidity, (int, float)):
            return 0
        
        if liquidity >= 500000:
            return 95
        elif liquidity >= 100000:
            return 80
        elif liquidity >= 50000:
            return 65
        elif liquidity >= 20000:
            return 50
        elif liquidity >= 10000:
            return 35
        elif liquidity >= 5000:
            return 20
        else:
            return 10
    
    def _generate_report(self, session: AnalysisSession, onchain_data: Dict,
                         market_data: Dict, social_data: Dict,
                         whale_data: Dict, simulation: SimulationResult) -> Dict[str, Any]:
        """Generate comprehensive AI analysis report using LLM"""
        
        metrics = market_data.get("metrics", {})
        
        prompt = f"""Generate a comprehensive memecoin trading analysis report.

TOKEN DATA:
- Address: {session.token_address}
- Chain: {session.chain}
- Price: ${metrics.get('price_usd', 0)}
- 24h Change: {metrics.get('price_change', {}).get('24h', 0)}%
- Volume 24h: ${metrics.get('volume', {}).get('24h', 0):,.0f}
- Liquidity: ${metrics.get('liquidity_usd', 0):,.0f}
- Market Cap: ${metrics.get('market_cap', 0):,.0f}

ON-CHAIN SAFETY:
- Safety Score: {onchain_data.get('overall_safety_score', 0)}/100
- Risk Level: {onchain_data.get('risk_level', 'unknown')}
- Risk Factors: {json.dumps(onchain_data.get('risk_factors', []))}
- Safety Factors: {json.dumps(onchain_data.get('safety_factors', []))}

SOCIAL SENTIMENT:
- Sentiment Score: {social_data.get('overall_sentiment', 0)}
- Sentiment Label: {social_data.get('sentiment_label', 'neutral')}
- Trending Score: {social_data.get('trending_score', 0)}

WHALE ACTIVITY:
- Pattern: {whale_data.get('pattern', 'unknown')}
- Top Holder %: {whale_data.get('top_holder_pct', 0)}%

MULTI-AGENT SIMULATION ({simulation.total_agents} agents, {simulation.rounds_completed} rounds):
- Buy: {simulation.buy_percentage}%
- Sell: {simulation.sell_percentage}%
- Hold: {simulation.hold_percentage}%
- Consensus: {simulation.consensus_action}
- Confidence: {simulation.consensus_strength}
- Predicted 1h: ${simulation.predicted_price_1h}
- Predicted 24h: ${simulation.predicted_price_24h}

Generate a JSON response with:
{{
    "summary": "2-3 sentence executive summary",
    "recommendation": "BUY" or "SELL" or "HOLD" or "AVOID",
    "confidence": float 0-1,
    "key_findings": ["finding 1", "finding 2", ...],
    "risk_factors": ["risk 1", "risk 2", ...],
    "bullish_factors": ["bull 1", "bull 2", ...],
    "bearish_factors": ["bear 1", "bear 2", ...],
    "markdown": "Full markdown report with sections: ## Executive Summary, ## On-Chain Analysis, ## Market Metrics, ## Social Sentiment, ## Whale Activity, ## Simulation Results, ## Risk Assessment, ## Recommendation"
}}

Be specific, data-driven, and actionable. If risk is high, say AVOID clearly.
Respond ONLY with valid JSON."""

        try:
            response = self.llm.chat(prompt, temperature=Config.REPORT_AGENT_TEMPERATURE)
            
            try:
                report = json.loads(response)
            except json.JSONDecodeError:
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                    report = json.loads(json_str)
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                    report = json.loads(json_str)
                else:
                    report = {
                        "summary": "Analysis complete but report formatting failed.",
                        "recommendation": simulation.consensus_action,
                        "confidence": simulation.consensus_strength,
                        "key_findings": [],
                        "risk_factors": onchain_data.get("risk_factors", []),
                        "bullish_factors": [],
                        "bearish_factors": [],
                        "markdown": response
                    }
            
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "summary": f"Analysis failed: {str(e)}",
                "recommendation": "HOLD",
                "confidence": 0,
                "key_findings": [],
                "risk_factors": [str(e)],
                "bullish_factors": [],
                "bearish_factors": [],
                "markdown": f"# Analysis Error\n\n{str(e)}"
            }
    
    # === Storage ===
    
    def _save_session(self, session: AnalysisSession):
        """Save session to disk atomically"""
        from ..utils import atomic_write_json
        path = os.path.join(self.data_dir, f"{session.session_id}.json")
        atomic_write_json(path, session.to_dict())
