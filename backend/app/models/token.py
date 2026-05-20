"""
Token Model - Represents a memecoin being tracked/analyzed
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TokenStatus(str, Enum):
    """Token tracking status"""
    DISCOVERED = "discovered"       # Newly found, not yet analyzed
    ANALYZING = "analyzing"         # Currently being analyzed
    TRACKED = "tracked"             # Actively being monitored
    ALERT = "alert"                 # Triggered alert conditions
    ARCHIVED = "archived"           # No longer actively tracked


class TokenRiskLevel(str, Enum):
    """Risk assessment level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class TokenMetrics(BaseModel):
    """Real-time token metrics"""
    price_usd: float = 0.0
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0
    price_change_7d: float = 0.0
    market_cap: float = 0.0
    volume_24h: float = 0.0
    liquidity_usd: float = 0.0
    holders_count: int = 0
    tx_count_24h: int = 0
    buy_count_24h: int = 0
    sell_count_24h: int = 0
    unique_wallets_24h: int = 0
    top10_holders_pct: float = 0.0  # % held by top 10 wallets
    updated_at: Optional[str] = None


class TokenSocial(BaseModel):
    """Social media metrics for a token"""
    twitter_mentions_1h: int = 0
    twitter_mentions_24h: int = 0
    twitter_sentiment_score: float = 0.0  # -1.0 to 1.0
    telegram_members: int = 0
    telegram_messages_24h: int = 0
    reddit_mentions_24h: int = 0
    influencer_mentions: List[Dict[str, Any]] = Field(default_factory=list)
    trending_score: float = 0.0  # 0.0 to 1.0
    updated_at: Optional[str] = None


class TokenOnChain(BaseModel):
    """On-chain analysis data"""
    contract_address: str = ""
    chain: str = "solana"  # solana, ethereum, bsc
    deployer_wallet: str = ""
    deploy_date: Optional[str] = None
    is_renounced: bool = False
    is_mint_disabled: bool = False
    is_freeze_disabled: bool = False
    has_blacklist: bool = False
    lp_locked: bool = False
    lp_lock_duration_days: int = 0
    honeypot_risk: bool = False
    tax_buy_pct: float = 0.0
    tax_sell_pct: float = 0.0
    max_wallet_pct: float = 0.0
    whale_wallets: List[Dict[str, Any]] = Field(default_factory=list)
    smart_money_wallets: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: Optional[str] = None


class Token(BaseModel):
    """Complete token data model"""
    token_id: str = Field(default_factory=lambda: f"tok_{uuid.uuid4().hex[:12]}")
    name: str = ""
    symbol: str = ""
    contract_address: str = ""
    chain: str = "solana"
    
    # Status & Risk
    status: TokenStatus = TokenStatus.DISCOVERED
    risk_level: TokenRiskLevel = TokenRiskLevel.UNKNOWN
    risk_score: float = 0.0  # 0.0 (safe) to 1.0 (rug)
    risk_factors: List[str] = Field(default_factory=list)
    
    # Composite Data
    metrics: TokenMetrics = Field(default_factory=TokenMetrics)
    social: TokenSocial = Field(default_factory=TokenSocial)
    on_chain: TokenOnChain = Field(default_factory=TokenOnChain)
    
    # AI Analysis
    ai_summary: str = ""
    ai_recommendation: str = ""  # BUY_SIGNAL, SELL_SIGNAL, HOLD, AVOID
    ai_confidence: float = 0.0
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Token":
        return cls(**data)
