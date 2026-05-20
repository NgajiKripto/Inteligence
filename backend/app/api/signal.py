"""
Signal API - Endpoints for trading signals, alerts, and whale tracking
"""

import traceback
from flask import request, jsonify

from . import signal_bp
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('memecoin.api.signal')


@signal_bp.route('/list', methods=['GET'])
def get_signals():
    """
    Get active trading signals
    
    Query params:
        type: signal type filter (optional)
        strength: minimum strength filter (optional)
        chain: chain filter (optional)
        token_id: filter by token (optional)
        limit: max results (default: 50)
        active_only: only show active signals (default: true)
    """
    try:
        signal_type = request.args.get('type', '')
        min_strength = request.args.get('strength', '')
        chain = request.args.get('chain', 'all')
        token_id = request.args.get('token_id', '')
        limit = request.args.get('limit', 50, type=int)
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        from ..services.signal_generator import SignalGenerator
        generator = SignalGenerator()
        
        signals = generator.get_signals(
            signal_type=signal_type,
            min_strength=min_strength,
            chain=chain,
            token_id=token_id,
            limit=limit,
            active_only=active_only
        )
        
        return jsonify({
            "success": True,
            "data": {
                "signals": [s.to_dict() for s in signals],
                "count": len(signals)
            }
        })
        
    except Exception as e:
        logger.error(f"Get signals failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@signal_bp.route('/whale-activity', methods=['GET'])
def get_whale_activity():
    """
    Get recent whale wallet activity
    
    Query params:
        chain: solana|ethereum|bsc (default: solana)
        min_amount_usd: minimum transaction USD value (default: 50000)
        hours: lookback period in hours (default: 24)
        limit: max results (default: 50)
    """
    try:
        chain = request.args.get('chain', 'solana')
        min_amount = request.args.get('min_amount_usd', 50000, type=float)
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        from ..services.whale_tracker import WhaleTracker
        tracker = WhaleTracker()
        
        activities = tracker.get_recent_activity(
            chain=chain,
            min_amount_usd=min_amount,
            hours=hours,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "data": {
                "activities": activities,
                "count": len(activities),
                "chain": chain,
                "timeframe_hours": hours
            }
        })
        
    except Exception as e:
        logger.error(f"Get whale activity failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@signal_bp.route('/smart-money', methods=['GET'])
def get_smart_money():
    """
    Track smart money wallets and their recent trades
    
    Query params:
        chain: solana|ethereum|bsc (default: solana)
        action: buy|sell|all (default: all)
        hours: lookback period (default: 24)
        limit: max results (default: 30)
    """
    try:
        chain = request.args.get('chain', 'solana')
        action = request.args.get('action', 'all')
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 30, type=int)
        
        from ..services.whale_tracker import WhaleTracker
        tracker = WhaleTracker()
        
        trades = tracker.get_smart_money_trades(
            chain=chain,
            action=action,
            hours=hours,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "data": {
                "trades": trades,
                "count": len(trades),
                "chain": chain
            }
        })
        
    except Exception as e:
        logger.error(f"Get smart money failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@signal_bp.route('/sentiment', methods=['GET'])
def get_market_sentiment():
    """
    Get overall market sentiment for memecoins
    
    Query params:
        chain: solana|ethereum|bsc|all (default: all)
        timeframe: 1h|6h|24h|7d (default: 24h)
    """
    try:
        chain = request.args.get('chain', 'all')
        timeframe = request.args.get('timeframe', '24h')
        
        from ..services.sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        sentiment = analyzer.get_market_sentiment(
            chain=chain,
            timeframe=timeframe
        )
        
        return jsonify({
            "success": True,
            "data": sentiment
        })
        
    except Exception as e:
        logger.error(f"Get sentiment failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@signal_bp.route('/new-pairs', methods=['GET'])
def get_new_pairs():
    """
    Get newly created token pairs (potential early entries)
    
    Query params:
        chain: solana|ethereum|bsc (default: solana)
        hours: how far back to look (default: 24)
        min_liquidity: minimum liquidity USD (default: 1000)
        limit: max results (default: 30)
    """
    try:
        chain = request.args.get('chain', 'solana')
        hours = request.args.get('hours', 24, type=int)
        min_liquidity = request.args.get('min_liquidity', 1000, type=float)
        limit = request.args.get('limit', 30, type=int)
        
        from ..services.token_scanner import TokenScanner
        scanner = TokenScanner()
        
        pairs = scanner.get_new_pairs(
            chain=chain,
            hours=hours,
            min_liquidity=min_liquidity,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "data": {
                "pairs": pairs,
                "count": len(pairs),
                "chain": chain,
                "timeframe_hours": hours
            }
        })
        
    except Exception as e:
        logger.error(f"Get new pairs failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@signal_bp.route('/rug-check/<token_address>', methods=['GET'])
def rug_check(token_address: str):
    """
    Quick rug-pull risk check for a token
    
    Returns safety score and specific risk indicators
    """
    try:
        chain = request.args.get('chain', 'solana')
        
        from ..services.risk_assessor import RiskAssessor
        assessor = RiskAssessor()
        
        result = assessor.quick_rug_check(
            token_address=token_address,
            chain=chain
        )
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Rug check failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
