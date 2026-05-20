"""
Analysis API - Endpoints for AI-powered memecoin analysis and simulation
"""

import traceback
import threading
from flask import request, jsonify

from . import analysis_bp
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('memecoin.api.analysis')


@analysis_bp.route('/start', methods=['POST'])
def start_analysis():
    """
    Start a comprehensive AI analysis session for a token
    
    This triggers the full pipeline:
    1. On-chain data collection & safety check
    2. Social sentiment analysis
    3. Whale/smart money tracking
    4. Multi-agent trading simulation
    5. Report generation with recommendation
    
    Request (JSON):
        {
            "token_address": "So11...abc",
            "chain": "solana",
            "analysis_depth": "standard",   // quick|standard|deep
            "simulate": true,               // run multi-agent simulation
            "agent_count": 50               // number of simulation agents
        }
    
    Returns immediately with session_id for progress polling
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
        
        # Validate agent count
        agent_count = min(agent_count, Config.SIMULATION_MAX_AGENTS)
        
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
                logger.error(f"Analysis failed: {str(e)}")
        
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
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@analysis_bp.route('/status/<session_id>', methods=['GET'])
def get_analysis_status(session_id: str):
    """
    Get analysis session status and progress
    
    Returns:
        {
            "session_id": "sess_xxxx",
            "status": "analyzing_social",
            "progress": 45,
            "current_step": "Analyzing Twitter sentiment...",
            "partial_results": {...}
        }
    """
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
            "error": str(e)
        }), 500


@analysis_bp.route('/report/<session_id>', methods=['GET'])
def get_analysis_report(session_id: str):
    """
    Get the completed analysis report
    
    Returns full markdown report with:
    - Executive summary
    - On-chain safety assessment
    - Social sentiment analysis
    - Whale/smart money activity
    - Multi-agent simulation results
    - Risk factors
    - Recommendation & confidence level
    """
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
            "error": str(e)
        }), 500


@analysis_bp.route('/simulate', methods=['POST'])
def run_simulation():
    """
    Run multi-agent trading simulation for a token
    
    Creates a virtual trading environment with diverse AI agents
    that make buy/sell/hold decisions based on available data.
    
    Request (JSON):
        {
            "token_address": "So11...abc",
            "chain": "solana",
            "agent_count": 50,
            "rounds": 10,
            "scenario": "neutral",     // bullish|neutral|bearish|crash
            "inject_event": ""         // optional: simulate an event
        }
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
        
        return jsonify({
            "success": True,
            "data": result.model_dump() if hasattr(result, 'model_dump') else result
        })
        
    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@analysis_bp.route('/chat', methods=['POST'])
def chat_with_analyst():
    """
    Chat with the AI analyst about a token or the market
    
    The AI analyst has access to all collected data, on-chain info,
    social sentiment, and simulation results.
    
    Request (JSON):
        {
            "message": "Is this token safe to buy?",
            "session_id": "sess_xxxx",      // optional, for context
            "token_address": "So11...abc",  // optional, for context
            "chat_history": [...]            // optional
        }
    """
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
            "error": str(e)
        }), 500


@analysis_bp.route('/history', methods=['GET'])
def get_analysis_history():
    """
    Get past analysis sessions
    
    Query params:
        limit: max results (default: 20)
        status: filter by status (optional)
    """
    try:
        limit = request.args.get('limit', 20, type=int)
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
            "error": str(e)
        }), 500
