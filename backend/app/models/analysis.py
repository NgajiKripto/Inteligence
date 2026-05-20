"""
Analysis Session Model - Tracks AI analysis sessions and reports
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    """Status of an analysis session"""
    CREATED = "created"
    COLLECTING_DATA = "collecting_data"
    ANALYZING_ONCHAIN = "analyzing_onchain"
    ANALYZING_SOCIAL = "analyzing_social"
    RUNNING_SIMULATION = "running_simulation"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentProfile(BaseModel):
    """Profile for a simulation agent"""
    agent_id: str = Field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    persona: str = ""  # e.g., "degen_trader", "whale", "paper_hands", "diamond_hands"
    risk_appetite: float = 0.5  # 0.0 conservative - 1.0 degen
    capital_usd: float = 1000.0
    experience_level: str = "intermediate"
    bias: str = "neutral"  # bullish, bearish, neutral
    twitter_influence: int = 0  # follower count simulation
    strategy: str = ""  # e.g., "momentum", "contrarian", "sniper", "holder"


class SimulationResult(BaseModel):
    """Result from multi-agent simulation"""
    simulation_id: str = Field(default_factory=lambda: f"sim_{uuid.uuid4().hex[:12]}")
    total_agents: int = 0
    rounds_completed: int = 0
    
    # Aggregated Predictions
    buy_percentage: float = 0.0
    sell_percentage: float = 0.0
    hold_percentage: float = 0.0
    
    # Price Predictions
    predicted_price_1h: Optional[float] = None
    predicted_price_24h: Optional[float] = None
    predicted_price_7d: Optional[float] = None
    price_confidence: float = 0.0
    
    # Sentiment Evolution
    sentiment_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Notable Agent Actions
    notable_actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Consensus
    consensus_action: str = ""  # BUY, SELL, HOLD, AVOID
    consensus_strength: float = 0.0


class AnalysisSession(BaseModel):
    """Complete analysis session for a token"""
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    token_id: str = ""
    token_symbol: str = ""
    token_address: str = ""
    chain: str = "solana"
    
    # Status
    status: AnalysisStatus = AnalysisStatus.CREATED
    progress: int = 0  # 0-100
    current_step: str = ""
    error: Optional[str] = None
    
    # Analysis Components
    on_chain_score: float = 0.0  # 0-100 safety score
    social_score: float = 0.0   # 0-100 hype/sentiment score
    liquidity_score: float = 0.0  # 0-100 liquidity health
    risk_score: float = 0.0     # 0-1.0 overall risk
    
    # Simulation
    simulation: Optional[SimulationResult] = None
    agent_profiles: List[AgentProfile] = Field(default_factory=list)
    
    # Report
    report_markdown: str = ""
    report_summary: str = ""
    recommendation: str = ""  # BUY, SELL, HOLD, AVOID
    confidence: float = 0.0
    
    # Key Findings
    key_findings: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    bullish_factors: List[str] = Field(default_factory=list)
    bearish_factors: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisSession":
        return cls(**data)
