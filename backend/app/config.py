"""
MemeCoin Intelligence - Configuration Manager
Loads all configuration from .env file at project root
"""

import os
from dotenv import load_dotenv

# Load .env from project root
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    load_dotenv(override=True)


class Config:
    """Application Configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'memecoin-intel-secret')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    JSON_AS_ASCII = False
    
    # LLM Configuration (OpenAI-compatible format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Blockchain RPC Endpoints
    SOLANA_RPC_URL = os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    ETH_RPC_URL = os.environ.get('ETH_RPC_URL', '')
    BSC_RPC_URL = os.environ.get('BSC_RPC_URL', '')
    
    # DEX & Price Data APIs
    DEXSCREENER_API_URL = os.environ.get('DEXSCREENER_API_URL', 'https://api.dexscreener.com/latest')
    BIRDEYE_API_KEY = os.environ.get('BIRDEYE_API_KEY', '')
    JUPITER_API_URL = os.environ.get('JUPITER_API_URL', 'https://quote-api.jup.ag/v6')
    
    # Social Media APIs
    TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN', '')
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID', '')
    REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET', '')
    
    # On-Chain Analysis
    HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY', '')  # Solana enhanced RPC
    SOLSCAN_API_KEY = os.environ.get('SOLSCAN_API_KEY', '')
    
    # Data Storage
    DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
    UPLOADS_DIR = os.path.join(os.path.dirname(__file__), '../uploads')
    
    # Analysis Configuration
    SENTIMENT_UPDATE_INTERVAL = int(os.environ.get('SENTIMENT_UPDATE_INTERVAL', '60'))  # seconds
    WHALE_ALERT_THRESHOLD_SOL = float(os.environ.get('WHALE_ALERT_THRESHOLD_SOL', '100'))
    WHALE_ALERT_THRESHOLD_USD = float(os.environ.get('WHALE_ALERT_THRESHOLD_USD', '50000'))
    MAX_TRACKED_TOKENS = int(os.environ.get('MAX_TRACKED_TOKENS', '50'))
    
    # Agent Simulation
    SIMULATION_MAX_AGENTS = int(os.environ.get('SIMULATION_MAX_AGENTS', '100'))
    SIMULATION_MAX_ROUNDS = int(os.environ.get('SIMULATION_MAX_ROUNDS', '20'))
    AGENT_TEMPERATURE = float(os.environ.get('AGENT_TEMPERATURE', '0.7'))
    
    # Report Agent
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '8'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.4'))
    
    # Risk Thresholds
    RISK_SCORE_HIGH = float(os.environ.get('RISK_SCORE_HIGH', '0.7'))
    RISK_SCORE_CRITICAL = float(os.environ.get('RISK_SCORE_CRITICAL', '0.9'))
    
    # Security
    API_AUTH_KEY = os.environ.get('API_AUTH_KEY', '')  # If empty, auth is disabled (dev mode)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not configured")
        return errors
