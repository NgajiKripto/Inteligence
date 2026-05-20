"""
Token Scanner Service - Discovers, tracks, and manages memecoin tokens
Integrates with DexScreener, Birdeye, and on-chain data
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import requests

from ..config import Config
from ..models.token import Token, TokenStatus, TokenRiskLevel, TokenMetrics, TokenSocial, TokenOnChain
from ..utils.logger import get_logger

logger = get_logger('memecoin.services.scanner')


class TokenScanner:
    """Discovers and manages memecoin tokens"""
    
    def __init__(self):
        self.data_dir = os.path.join(Config.DATA_DIR, 'tokens')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def discover_token(self, contract_address: str, chain: str = "solana", auto_track: bool = True) -> Token:
        """
        Discover a token by contract address.
        Fetches basic data from DexScreener and creates a Token record.
        """
        logger.info(f"Discovering token: {contract_address} on {chain}")
        
        # Check if already tracked
        existing = self._find_by_address(contract_address)
        if existing:
            logger.info(f"Token already tracked: {existing.token_id}")
            return existing
        
        # Fetch from DexScreener
        token_data = self._fetch_dexscreener(contract_address)
        
        # Build token model
        token = Token(
            contract_address=contract_address,
            chain=chain,
            name=token_data.get('name', 'Unknown'),
            symbol=token_data.get('symbol', '???'),
            status=TokenStatus.TRACKED if auto_track else TokenStatus.DISCOVERED,
        )
        
        # Populate metrics
        token.metrics = TokenMetrics(
            price_usd=token_data.get('price_usd', 0),
            price_change_24h=token_data.get('price_change_24h', 0),
            market_cap=token_data.get('market_cap', 0),
            volume_24h=token_data.get('volume_24h', 0),
            liquidity_usd=token_data.get('liquidity_usd', 0),
            updated_at=datetime.now().isoformat()
        )
        
        # Populate on-chain info
        token.on_chain = TokenOnChain(
            contract_address=contract_address,
            chain=chain,
            deploy_date=token_data.get('pair_created_at', ''),
            updated_at=datetime.now().isoformat()
        )
        
        # Save token
        self._save_token(token)
        logger.info(f"Token discovered: {token.symbol} ({token.token_id})")
        
        return token
    
    def get_trending(self, chain: str = "all", timeframe: str = "24h",
                     limit: int = 20, sort_by: str = "volume") -> List[Token]:
        """Get trending tokens from DexScreener boosted/trending endpoint"""
        logger.info(f"Fetching trending tokens: chain={chain}, sort={sort_by}")
        
        try:
            # DexScreener trending endpoint
            url = f"{Config.DEXSCREENER_API_URL}/dex/tokens/trending"
            if chain != "all":
                url = f"{Config.DEXSCREENER_API_URL}/dex/pairs/{chain}"
            
            resp = requests.get(url, timeout=10)
            pairs = []
            
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get('pairs', [])[:limit]
            
            # Convert to Token objects
            tokens = []
            for pair in pairs:
                token = Token(
                    name=pair.get('baseToken', {}).get('name', 'Unknown'),
                    symbol=pair.get('baseToken', {}).get('symbol', '???'),
                    contract_address=pair.get('baseToken', {}).get('address', ''),
                    chain=pair.get('chainId', chain),
                    status=TokenStatus.DISCOVERED,
                    metrics=TokenMetrics(
                        price_usd=float(pair.get('priceUsd', 0) or 0),
                        price_change_24h=float(pair.get('priceChange', {}).get('h24', 0) or 0),
                        volume_24h=float(pair.get('volume', {}).get('h24', 0) or 0),
                        liquidity_usd=float(pair.get('liquidity', {}).get('usd', 0) or 0),
                        updated_at=datetime.now().isoformat()
                    )
                )
                tokens.append(token)
            
            # Sort
            if sort_by == "volume":
                tokens.sort(key=lambda t: t.metrics.volume_24h, reverse=True)
            elif sort_by == "gainers":
                tokens.sort(key=lambda t: t.metrics.price_change_24h, reverse=True)
            elif sort_by == "holders":
                tokens.sort(key=lambda t: t.metrics.holders_count, reverse=True)
            
            return tokens[:limit]
            
        except Exception as e:
            logger.error(f"Failed to fetch trending: {e}")
            return []
    
    def get_watchlist(self, status: str = "all", sort_by: str = "risk") -> List[Token]:
        """Get all tracked tokens (watchlist)"""
        tokens = self._load_all_tokens()
        
        if status != "all":
            tokens = [t for t in tokens if t.status.value == status]
        
        if sort_by == "risk":
            tokens.sort(key=lambda t: t.risk_score, reverse=True)
        elif sort_by == "volume":
            tokens.sort(key=lambda t: t.metrics.volume_24h, reverse=True)
        elif sort_by == "price_change":
            tokens.sort(key=lambda t: t.metrics.price_change_24h, reverse=True)
        
        return tokens
    
    def get_token(self, token_id: str) -> Optional[Token]:
        """Get a single token by ID"""
        path = os.path.join(self.data_dir, f"{token_id}.json")
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        return Token.from_dict(data)
    
    def remove_token(self, token_id: str) -> bool:
        """Remove token from watchlist"""
        path = os.path.join(self.data_dir, f"{token_id}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    
    def search(self, query: str, chain: str = "all") -> List[Token]:
        """Search tokens by name or symbol"""
        tokens = self._load_all_tokens()
        query_lower = query.lower()
        
        results = [
            t for t in tokens
            if query_lower in t.name.lower() or query_lower in t.symbol.lower()
        ]
        
        if chain != "all":
            results = [t for t in results if t.chain == chain]
        
        return results
    
    def get_new_pairs(self, chain: str = "solana", hours: int = 24,
                      min_liquidity: float = 1000, limit: int = 30) -> List[Dict[str, Any]]:
        """Get newly created trading pairs"""
        try:
            url = f"{Config.DEXSCREENER_API_URL}/dex/pairs/{chain}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            pairs = data.get('pairs', [])
            
            # Filter by time and liquidity
            cutoff = datetime.now() - timedelta(hours=hours)
            new_pairs = []
            
            for pair in pairs:
                created = pair.get('pairCreatedAt', '')
                liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                
                if liquidity >= min_liquidity:
                    new_pairs.append({
                        "pair_address": pair.get('pairAddress', ''),
                        "token_name": pair.get('baseToken', {}).get('name', ''),
                        "token_symbol": pair.get('baseToken', {}).get('symbol', ''),
                        "token_address": pair.get('baseToken', {}).get('address', ''),
                        "price_usd": float(pair.get('priceUsd', 0) or 0),
                        "liquidity_usd": liquidity,
                        "volume_24h": float(pair.get('volume', {}).get('h24', 0) or 0),
                        "price_change_24h": float(pair.get('priceChange', {}).get('h24', 0) or 0),
                        "chain": chain,
                        "created_at": created
                    })
            
            return new_pairs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to fetch new pairs: {e}")
            return []
    
    # === Private Methods ===
    
    def _fetch_dexscreener(self, address: str) -> Dict[str, Any]:
        """Fetch token data from DexScreener API"""
        try:
            url = f"{Config.DEXSCREENER_API_URL}/dex/tokens/{address}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code != 200:
                logger.warning(f"DexScreener returned {resp.status_code} for {address}")
                return {"name": "Unknown", "symbol": "???"}
            
            data = resp.json()
            pairs = data.get('pairs', [])
            
            if not pairs:
                return {"name": "Unknown", "symbol": "???"}
            
            # Use the pair with highest liquidity
            pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0) or 0))
            
            return {
                "name": pair.get('baseToken', {}).get('name', 'Unknown'),
                "symbol": pair.get('baseToken', {}).get('symbol', '???'),
                "price_usd": float(pair.get('priceUsd', 0) or 0),
                "price_change_24h": float(pair.get('priceChange', {}).get('h24', 0) or 0),
                "market_cap": float(pair.get('marketCap', 0) or 0),
                "volume_24h": float(pair.get('volume', {}).get('h24', 0) or 0),
                "liquidity_usd": float(pair.get('liquidity', {}).get('usd', 0) or 0),
                "pair_created_at": pair.get('pairCreatedAt', ''),
            }
            
        except Exception as e:
            logger.error(f"DexScreener fetch failed: {e}")
            return {"name": "Unknown", "symbol": "???"}
    
    def _save_token(self, token: Token):
        """Persist token to disk atomically"""
        from ..utils import atomic_write_json
        path = os.path.join(self.data_dir, f"{token.token_id}.json")
        atomic_write_json(path, token.to_dict())
    
    def _load_all_tokens(self) -> List[Token]:
        """Load all saved tokens"""
        tokens = []
        if not os.path.exists(self.data_dir):
            return tokens
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                path = os.path.join(self.data_dir, filename)
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    tokens.append(Token.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to load token {filename}: {e}")
        
        return tokens
    
    def _find_by_address(self, address: str) -> Optional[Token]:
        """Find a token by contract address"""
        tokens = self._load_all_tokens()
        for token in tokens:
            if token.contract_address == address:
                return token
        return None
