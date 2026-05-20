"""
Analysis API - Endpoints for AI-powered memecoin analysis and simulation
"""

import threading
from flask import request, jsonify

from . import analysis_bp
from ..config import Config
from ..utils.logger import get_logger
from ..utils import require_api_key, rate_limit, validate_contract_address

logger = get_logger('memecoin.api.analysis')


@analysis_bp.route('/start', methods=['POST'])
@require_api_key
@rate_limit(max_requests=5, window_seconds=300)
def start_analysis():
    """
    Start a comprehensive AI analysis session for a token.
    Returns immediately with session_id for progress polling.
    """
    try:
        data = request.get_json() or {}
        
        token_address = data.get('token_address', '').strip()
        chain = data.get('chain', 'solana')
        analysis_depth = data.get('analysis_depth', 'standard')
        simulate = data.get('simulate', True)
        agent_count = data.get('agent_count', 50)
        
        if not token_address:
            return jsonify({
                "success": False,
                "error": "token_address is required"
            }), 400
        
        # Validate address format
        if not validate_contract_address(token_address, chain):
            return jsonify({
                "success": False,
                "error": f"Invalid contract address format for chain '{chain}'"
            }), 400
        
        # Validate and cap agent count
        agent_count = min(max(int(agent_count), 5), Config.SIMULATION_MAX_AGENTS)
        
        from ..services.analysis_engine import AnalysisEngine
        engine = AnalysisEngine()
        
        # Create session
        session = engine.create_session(
            token_address=token_address,
            chain=chain,
            analysis_depth=analysis_depth,
            simulate=simulate,
            agent_count=agent_count
        )
        
        # Run analysis in background
        def run_analysis():
            try:
                engine.run_full_analysis(session.session_id)
            except Exception as e:
                logger.error(f"Background analysis failed: {str(e)}")
        
        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "session_id": session.session_id,
                "token_address": token_address,
                "chain": chain,
                "status": "collecting_data",
                "message": "Analysis started. Poll /api/analysis/status for progress."
            }
        })
        
    except Exception as e:
        logger.error(f"Start analysis failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to start analysis. Please check your input and try again."
        }), 500


@analysis_bp.route('/status/<session_id>', methods=['GET'])
def get_analysis_status(session_id: str):
    """Get analysis session status and progress"""
    try:
        from ..services.analysis_engine import AnalysisEngine
        engine = AnalysisEngine()
        
        session = engine.get_session(session_id)
        if not session:
            return jsonify({
                "success": False,
                "error": f"Session {session_id} not found"
            }), 404
        
        return jsonify({
            "success": True,
            "data": session.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Get status failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get session status"
        }), 500


@analysis_bp.route('/report/<session_id>', methods=['GET'])
def get_analysis_report(session_id: str):
    """Get the completed analysis report"""
    try:
        from ..services.analysis_engine import AnalysisEngine
        engine = AnalysisEngine()
        
        session = engine.get_session(session_id)
        if not session:
            return jsonify({
                "success": False,
                "error": f"Session {session_id} not found"
            }), 404
        
        if session.status != "completed":
            return jsonify({
                "success": False,
                "error": f"Analysis not completed. Current status: {session.status}",
                "progress": session.progress
            }), 400
        
        return jsonify({
            "success": True,
            "data": {
                "session_id": session_id,
                "report": session.report_markdown,
                "summary": session.report_summary,
                "recommendation": session.recommendation,
                "confidence": session.confidence,
                "key_findings": session.key_findings,
                "risk_factors": session.risk_factors,
                "bullish_factors": session.bullish_factors,
                "bearish_factors": session.bearish_factors,
                "simulation": session.simulation.model_dump() if session.simulation else None
            }
        })
        
    except Exception as e:
        logger.error(f"Get report failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve report"
        }), 500


@analysis_bp.route('/simulate', methods=['POST'])
@require_api_key
@rate_limit(max_requests=3, window_seconds=300)
def run_simulation():
    """
    Run multi-agent trading simulation for a token (async).
    Returns a session_id to poll for results.
    """
    try:
        data = request.get_json() or {}
        
        token_address = data.get('token_address', '').strip()
        chain = data.get('chain', 'solana')
        agent_count = min(data.get('agent_count', 50), Config.SIMULATION_MAX_AGENTS)
        rounds = min(data.get('rounds', 10), Config.SIMULATION_MAX_ROUNDS)
        scenario = data.get('scenario', 'neutral')
        inject_event = data.get('inject_event', '')
        
        if not token_address:
            return jsonify({
                "success": False,
                "error": "token_address is required"
            }), 400
        
        # Validate address format
        if not validate_contract_address(token_address, chain):
            return jsonify({
                "success": False,
                "error": f"Invalid contract address format for chain '{chain}'"
            }), 400
        
        # Run simulation in background thread to avoid blocking
        import uuid
        sim_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        # Store placeholder result
        from ..services.analysis_engine import AnalysisEngine
        import os, json
        result_dir = os.path.join(Config.DATA_DIR, 'simulations')
        os.makedirs(result_dir, exist_ok=True)
        result_path = os.path.join(result_dir, f"{sim_id}.json")
        
        # Write initial status
        from ..utils import atomic_write_json
        atomic_write_json(result_path, {"status": "running", "sim_id": sim_id})
        
        def run_sim():
            try:
                from ..services.simulation_engine import SimulationEngine
                sim_engine = SimulationEngine()
                
                result = sim_engine.run_simulation(
                    token_address=token_address,
                    chain=chain,
                    agent_count=agent_count,
                    rounds=rounds,
                    scenario=scenario,
                    inject_event=inject_event
                )
                
                atomic_write_json(result_path, {
                    "status": "completed",
                    "sim_id": sim_id,
                    "data": result.model_dump() if hasattr(result, 'model_dump') else result
                })
            except Exception as e:
                logger.error(f"Simulation {sim_id} failed: {str(e)}")
                atomic_write_json(result_path, {
                    "status": "failed",
                    "sim_id": sim_id,
                    "error": str(e)
                })
        
        thread = threading.Thread(target=run_sim, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "sim_id": sim_id,
                "status": "running",
                "message": "Simulation started. Poll /api/analysis/simulate/status/<sim_id> for results."
            }
        })
        
    except Exception as e:
        logger.error(f"Simulation start failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to start simulation"
        }), 500


@analysis_bp.route('/simulate/status/<sim_id>', methods=['GET'])
def get_simulation_status(sim_id: str):
    """Get simulation result by sim_id"""
    try:
        import os, json
        result_dir = os.path.join(Config.DATA_DIR, 'simulations')
        result_path = os.path.join(result_dir, f"{sim_id}.json")
        
        if not os.path.exists(result_path):
            return jsonify({"success": False, "error": "Simulation not found"}), 404
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        return jsonify({"success": True, "data": result})
        
    except Exception as e:
        logger.error(f"Get simulation status failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get simulation status"}), 500


@analysis_bp.route('/chat', methods=['POST'])
@require_api_key
@rate_limit(max_requests=20, window_seconds=60)
def chat_with_analyst():
    """Chat with the AI analyst about a token or the market"""
    try:
        data = request.get_json() or {}
        
        message = data.get('message', '').strip()
        session_id = data.get('session_id', '')
        token_address = data.get('token_address', '')
        chat_history = data.get('chat_history', [])
        
        if not message:
            return jsonify({
                "success": False,
                "error": "message is required"
            }), 400
        
        # Limit message length
        if len(message) > 2000:
            return jsonify({
                "success": False,
                "error": "Message too long (max 2000 chars)"
            }), 400
        
        # Limit chat history
        chat_history = chat_history[-10:] if chat_history else []
        
        from ..services.analyst_agent import AnalystAgent
        agent = AnalystAgent()
        
        response = agent.chat(
            message=message,
            session_id=session_id,
            token_address=token_address,
            chat_history=chat_history
        )
        
        return jsonify({
            "success": True,
            "data": response
        })
        
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Chat request failed. Please try again."
        }), 500


@analysis_bp.route('/history', methods=['GET'])
@require_api_key
def get_analysis_history():
    """Get past analysis sessions"""
    try:
        limit = min(request.args.get('limit', 20, type=int), 100)
        status = request.args.get('status', '')
        
        from ..services.analysis_engine import AnalysisEngine
        engine = AnalysisEngine()
        
        sessions = engine.get_history(limit=limit, status=status)
        
        return jsonify({
            "success": True,
            "data": {
                "sessions": [s.to_dict() for s in sessions],
                "count": len(sessions)
            }
        })
        
    except Exception as e:
        logger.error(f"Get history failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get analysis history"
        }), 500




# === Learning & Strategy Endpoints ===

@analysis_bp.route('/learn', methods=['POST'])
@require_api_key
@rate_limit(max_requests=3, window_seconds=300)
def run_learning():
    """
    Run a learning cycle to improve future analysis.
    Analyzes past predictions vs actual outcomes and generates lessons.
    """
    try:
        data = request.get_json() or {}
        window_hours = min(data.get('window_hours', 24), 168)

        from ..services.learning_engine import LearningEngine
        engine = LearningEngine()
        result = engine.run_learning(window_hours=window_hours)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Learning failed: {str(e)}")
        return jsonify({"success": False, "error": "Learning cycle failed"}), 500


@analysis_bp.route('/lessons', methods=['GET'])
def get_active_lessons():
    """Get active lessons that influence future analysis"""
    try:
        from ..services.learning_engine import LearningEngine
        engine = LearningEngine()
        lessons = engine.get_active_lessons()
        history = engine.get_learning_history(limit=5)

        return jsonify({
            "success": True,
            "data": {
                "active_lessons": lessons,
                "recent_runs": history,
            }
        })

    except Exception as e:
        logger.error(f"Get lessons failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get lessons"}), 500


@analysis_bp.route('/strategies', methods=['GET'])
def list_strategies():
    """List available analysis strategies"""
    try:
        from ..services.strategy_manager import StrategyManager
        mgr = StrategyManager()
        return jsonify({"success": True, "data": mgr.list_strategies()})
    except Exception as e:
        logger.error(f"List strategies failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@analysis_bp.route('/strategies/active', methods=['PUT'])
@require_api_key
def set_active_strategy():
    """Set the active analysis strategy"""
    try:
        data = request.get_json() or {}
        strategy_id = data.get('strategy_id', '')

        if not strategy_id:
            return jsonify({"success": False, "error": "strategy_id required"}), 400

        from ..services.strategy_manager import StrategyManager
        mgr = StrategyManager()
        success = mgr.set_active_strategy(strategy_id)

        if not success:
            return jsonify({"success": False, "error": f"Strategy '{strategy_id}' not found"}), 404

        return jsonify({"success": True, "data": {"active_strategy": strategy_id}})

    except Exception as e:
        logger.error(f"Set strategy failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@analysis_bp.route('/ath-context/<token_address>', methods=['GET'])
@rate_limit(max_requests=30, window_seconds=60)
def get_ath_context(token_address: str):
    """Get ATH/range context and top-blast risk for a token"""
    try:
        chain = request.args.get('chain', 'solana')

        from ..services.ath_tracker import AthTracker
        tracker = AthTracker()
        result = tracker.get_ath_context(token_address, chain)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"ATH context failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get ATH context"}), 500


# === Signal Accuracy & Overlap ===

@analysis_bp.route('/signal-accuracy', methods=['GET'])
def get_signal_accuracy():
    """Get signal prediction accuracy stats"""
    try:
        hours = min(request.args.get('hours', 24, type=int), 168)

        from ..services.signal_accuracy import SignalAccuracyTracker
        tracker = SignalAccuracyTracker()
        result = tracker.calculate_accuracy(hours_lookback=hours)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Signal accuracy failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to calculate accuracy"}), 500


@analysis_bp.route('/signal-overlap', methods=['GET'])
def get_signal_overlaps():
    """Get tokens with multiple overlapping signals (high confidence)"""
    try:
        min_sources = request.args.get('min_sources', 2, type=int)

        from ..services.signal_overlap import get_overlap_scorer
        scorer = get_overlap_scorer()
        results = scorer.get_top_overlaps(min_sources=min_sources)

        return jsonify({"success": True, "data": {"overlaps": results, "count": len(results)}})

    except Exception as e:
        logger.error(f"Signal overlap failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get overlaps"}), 500


# === Wallet Watchlist ===

@analysis_bp.route('/wallets', methods=['GET'])
@require_api_key
def list_watched_wallets():
    """List tracked wallets"""
    try:
        from ..services.wallet_watchlist import WalletWatchlist
        wl = WalletWatchlist()
        return jsonify({"success": True, "data": wl.list_wallets()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analysis_bp.route('/wallets', methods=['POST'])
@require_api_key
def add_watched_wallet():
    """Add a wallet to watchlist"""
    try:
        data = request.get_json() or {}
        address = data.get('address', '').strip()
        label = data.get('label', '').strip()
        tags = data.get('tags', ['smart_money'])

        if not address or not label:
            return jsonify({"success": False, "error": "address and label required"}), 400

        from ..services.wallet_watchlist import WalletWatchlist
        wl = WalletWatchlist()
        result = wl.add_wallet(address, label, tags)

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        return jsonify({"success": True, "data": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analysis_bp.route('/wallets/<address>', methods=['DELETE'])
@require_api_key
def remove_watched_wallet(address: str):
    """Remove a wallet from watchlist"""
    try:
        from ..services.wallet_watchlist import WalletWatchlist
        wl = WalletWatchlist()
        success = wl.remove_wallet(address)

        if not success:
            return jsonify({"success": False, "error": "Wallet not found"}), 404

        return jsonify({"success": True, "message": "Wallet removed"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
