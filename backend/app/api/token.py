"""
Token API - Endpoints for memecoin tracking, discovery, and data retrieval
"""

import traceback
from flask import request, jsonify

from . import token_bp
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('memecoin.api.token')


@token_bp.route('/discover', methods=['POST'])
def discover_token():
    """
    Discover and analyze a new memecoin by contract address
    
    Request (JSON):
        {
            "contract_address": "So11...abc",
            "chain": "solana",             // optional, default: solana
            "auto_track": true             // optional, auto-add to watchlist
        }
    
    Returns token data with initial risk assessment
    """
    try:
        data = request.get_json() or {}
        contract_address = data.get('contract_address', '').strip()
        chain = data.get('chain', 'solana')
        auto_track = data.get('auto_track', True)
        
        if not contract_address:
            return jsonify({
                "success": False,
                "error": "contract_address is required"
            }), 400
        
        from ..services.token_scanner import TokenScanner
        scanner = TokenScanner()
        
        token = scanner.discover_token(
            contract_address=contract_address,
            chain=chain,
            auto_track=auto_track
        )
        
        return jsonify({
            "success": True,
            "data": token.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Token discovery failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@token_bp.route('/trending', methods=['GET'])
def get_trending_tokens():
    """
    Get trending memecoins based on volume, social mentions, and new listings
    
    Query params:
        chain: solana|ethereum|bsc (optional, default: all)
        timeframe: 1h|6h|24h (optional, default: 24h)
        limit: number of results (optional, default: 20)
        sort_by: volume|social|holders|gainers (optional, default: volume)
    """
    try:
        chain = request.args.get('chain', 'all')
        timeframe = request.args.get('timeframe', '24h')
        limit = request.args.get('limit', 20, type=int)
        sort_by = request.args.get('sort_by', 'volume')
        
        from ..services.token_scanner import TokenScanner
        scanner = TokenScanner()
        
        tokens = scanner.get_trending(
            chain=chain,
            timeframe=timeframe,
            limit=limit,
            sort_by=sort_by
        )
        
        return jsonify({
            "success": True,
            "data": {
                "tokens": [t.to_dict() for t in tokens],
                "count": len(tokens),
                "timeframe": timeframe,
                "chain": chain
            }
        })
        
    except Exception as e:
        logger.error(f"Get trending failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@token_bp.route('/watchlist', methods=['GET'])
def get_watchlist():
    """
    Get user's tracked tokens (watchlist)
    
    Query params:
        status: tracked|alert|all (optional, default: all)
        sort_by: risk|volume|price_change (optional, default: risk)
    """
    try:
        status = request.args.get('status', 'all')
        sort_by = request.args.get('sort_by', 'risk')
        
        from ..services.token_scanner import TokenScanner
        scanner = TokenScanner()
        
        tokens = scanner.get_watchlist(status=status, sort_by=sort_by)
        
        return jsonify({
            "success": True,
            "data": {
                "tokens": [t.to_dict() for t in tokens],
                "count": len(tokens)
            }
        })
        
    except Exception as e:
        logger.error(f"Get watchlist failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@token_bp.route('/<token_id>', methods=['GET'])
def get_token_detail(token_id: str):
    """Get detailed token data including metrics, social, on-chain"""
    try:
        from ..services.token_scanner import TokenScanner
        scanner = TokenScanner()
        
        token = scanner.get_token(token_id)
        if not token:
            return jsonify({
                "success": False,
                "error": f"Token {token_id} not found"
            }), 404
        
        return jsonify({
            "success": True,
            "data": token.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Get token failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@token_bp.route('/<token_id>/metrics', methods=['GET'])
def get_token_metrics(token_id: str):
    """Get real-time price and trading metrics for a token"""
    try:
        from ..services.price_tracker import PriceTracker
        tracker = PriceTracker()
        
        metrics = tracker.get_live_metrics(token_id)
        
        return jsonify({
            "success": True,
            "data": metrics
        })
        
    except Exception as e:
        logger.error(f"Get metrics failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@token_bp.route('/<token_id>/holders', methods=['GET'])
def get_token_holders(token_id: str):
    """
    Get holder analysis for a token
    
    Query params:
        top_n: number of top holders to return (default: 20)
    """
    try:
        top_n = request.args.get('top_n', 20, type=int)
        
        from ..services.onchain_analyzer import OnChainAnalyzer
        analyzer = OnChainAnalyzer()
        
        holders = analyzer.get_holder_analysis(token_id, top_n=top_n)
        
        return jsonify({
            "success": True,
            "data": holders
        })
        
    except Exception as e:
        logger.error(f"Get holders failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@token_bp.route('/<token_id>/risk', methods=['GET'])
def get_token_risk(token_id: str):
    """Get comprehensive risk assessment for a token"""
    try:
        from ..services.risk_assessor import RiskAssessor
        assessor = RiskAssessor()
        
        risk = assessor.assess_token(token_id)
        
        return jsonify({
            "success": True,
            "data": risk
        })
        
    except Exception as e:
        logger.error(f"Risk assessment failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@token_bp.route('/<token_id>', methods=['DELETE'])
def remove_token(token_id: str):
    """Remove token from watchlist"""
    try:
        from ..services.token_scanner import TokenScanner
        scanner = TokenScanner()
        
        success = scanner.remove_token(token_id)
        if not success:
            return jsonify({
                "success": False,
                "error": f"Token {token_id} not found"
            }), 404
        
        return jsonify({
            "success": True,
            "message": f"Token {token_id} removed from watchlist"
        })
        
    except Exception as e:
        logger.error(f"Remove token failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@token_bp.route('/search', methods=['GET'])
def search_tokens():
    """
    Search tokens by name or symbol
    
    Query params:
        q: search query (name or symbol)
        chain: filter by chain (optional)
    """
    try:
        query = request.args.get('q', '').strip()
        chain = request.args.get('chain', 'all')
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Query parameter 'q' is required"
            }), 400
        
        from ..services.token_scanner import TokenScanner
        scanner = TokenScanner()
        
        results = scanner.search(query=query, chain=chain)
        
        return jsonify({
            "success": True,
            "data": {
                "results": [t.to_dict() for t in results],
                "count": len(results)
            }
        })
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
