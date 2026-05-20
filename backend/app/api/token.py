"""
Token API - Endpoints for memecoin tracking, discovery, and data retrieval
"""

from flask import request, jsonify

from . import token_bp
from ..config import Config
from ..utils.logger import get_logger
from ..utils import require_api_key, rate_limit, validate_contract_address

logger = get_logger('memecoin.api.token')


@token_bp.route('/discover', methods=['POST'])
@require_api_key
@rate_limit(max_requests=10, window_seconds=60)
def discover_token():
    """
    Discover and analyze a new memecoin by contract address
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
        
        # Validate address format
        if not validate_contract_address(contract_address, chain):
            return jsonify({
                "success": False,
                "error": f"Invalid contract address format for chain '{chain}'"
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
            "error": "Token discovery failed. Please try again."
        }), 500


@token_bp.route('/trending', methods=['GET'])
@rate_limit(max_requests=30, window_seconds=60)
def get_trending_tokens():
    """Get trending memecoins based on volume, social mentions, and new listings"""
    try:
        chain = request.args.get('chain', 'all')
        timeframe = request.args.get('timeframe', '24h')
        limit = min(request.args.get('limit', 20, type=int), 100)
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
            "error": "Failed to fetch trending tokens"
        }), 500


@token_bp.route('/watchlist', methods=['GET'])
@require_api_key
def get_watchlist():
    """Get user's tracked tokens (watchlist)"""
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
            "error": "Failed to fetch watchlist"
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
            "error": "Failed to get token details"
        }), 500


@token_bp.route('/<token_id>/metrics', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def get_token_metrics(token_id: str):
    """Get real-time price and trading metrics for a token"""
    try:
        from ..services.price_tracker import PriceTracker
        tracker = PriceTracker.instance()
        
        metrics = tracker.get_live_metrics(token_id)
        
        return jsonify({
            "success": True,
            "data": metrics
        })
        
    except Exception as e:
        logger.error(f"Get metrics failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get token metrics"
        }), 500


@token_bp.route('/<token_id>/holders', methods=['GET'])
@rate_limit(max_requests=20, window_seconds=60)
def get_token_holders(token_id: str):
    """Get holder analysis for a token"""
    try:
        top_n = min(request.args.get('top_n', 20, type=int), 50)
        
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
            "error": "Failed to get holder analysis"
        }), 500


@token_bp.route('/<token_id>/risk', methods=['GET'])
@rate_limit(max_requests=20, window_seconds=60)
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
            "error": "Risk assessment failed"
        }), 500


@token_bp.route('/<token_id>', methods=['DELETE'])
@require_api_key
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
            "error": "Failed to remove token"
        }), 500


@token_bp.route('/search', methods=['GET'])
@rate_limit(max_requests=30, window_seconds=60)
def search_tokens():
    """Search tokens by name or symbol"""
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
            "error": "Search failed"
        }), 500
