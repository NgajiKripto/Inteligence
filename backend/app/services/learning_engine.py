"""
Learning Engine - Self-improvement loop inspired by Charon's learning module.
Analyzes past analysis sessions and predictions vs actual outcomes,
generates actionable lessons, and injects them into future LLM prompts.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient
from ..utils import atomic_write_json

logger = get_logger('memecoin.services.learning')


class LearningEngine:
    """
    Self-improvement feedback loop:
    1. Analyze completed analysis sessions in a time window
    2. Compare predictions with actual outcomes (price movement)
    3. Generate lessons via LLM or heuristics
    4. Store active lessons that get injected into future prompts
    """

    def __init__(self):
        self.llm = LLMClient()
        self.data_dir = os.path.join(Config.DATA_DIR, 'learning')
        self.lessons_file = os.path.join(self.data_dir, 'active_lessons.json')
        os.makedirs(self.data_dir, exist_ok=True)

    def run_learning(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        Run a learning cycle over the specified time window.
        
        1. Gather completed sessions
        2. For each, check actual price movement vs prediction
        3. Generate lessons from patterns
        4. Store lessons for future use
        """
        logger.info(f"Running learning cycle for last {window_hours}h")

        # Gather data
        summary = self._build_learning_summary(window_hours)

        if summary["total_sessions"] == 0:
            return {
                "status": "no_data",
                "message": f"No completed sessions in last {window_hours}h",
                "lessons": []
            }

        # Generate lessons
        lessons = self._generate_lessons(summary)

        # Store learning run
        run_id = self._store_learning_run(window_hours, summary, lessons)

        # Update active lessons
        self._update_active_lessons(lessons)

        logger.info(f"Learning run #{run_id}: {len(lessons)} lessons generated")

        return {
            "status": "completed",
            "run_id": run_id,
            "window_hours": window_hours,
            "summary": summary,
            "lessons": lessons
        }

    def get_active_lessons(self, limit: int = 6) -> List[str]:
        """Get active lessons for prompt injection"""
        if not os.path.exists(self.lessons_file):
            return []

        try:
            with open(self.lessons_file, 'r') as f:
                data = json.load(f)
            lessons = data.get("lessons", [])
            return [l["lesson"] for l in lessons[:limit]]
        except Exception:
            return []

    def get_lessons_for_prompt(self, max_chars: int = 1500) -> str:
        """Format active lessons for LLM prompt injection with token budget cap"""
        lessons = self.get_active_lessons()
        if not lessons:
            return ""

        # Cap total character count to avoid flooding LLM context
        formatted_lines = []
        total_chars = 0
        for lesson in lessons:
            line = f"- {lesson[:200]}"  # Cap each lesson at 200 chars
            if total_chars + len(line) > max_chars:
                break
            formatted_lines.append(line)
            total_chars += len(line)

        if not formatted_lines:
            return ""

        formatted = "\n".join(formatted_lines)
        return f"\nACTIVE LESSONS FROM PAST ANALYSIS (apply these):\n{formatted}\n"

    def get_learning_history(self, limit: int = 10) -> List[Dict]:
        """Get past learning runs"""
        runs_dir = os.path.join(self.data_dir, 'runs')
        if not os.path.exists(runs_dir):
            return []

        runs = []
        for filename in sorted(os.listdir(runs_dir), reverse=True)[:limit]:
            if filename.endswith('.json'):
                path = os.path.join(runs_dir, filename)
                try:
                    with open(path, 'r') as f:
                        runs.append(json.load(f))
                except Exception:
                    continue
        return runs

    # === Internal Methods ===

    def _build_learning_summary(self, window_hours: int) -> Dict[str, Any]:
        """Build summary of recent analysis performance"""
        from .analysis_engine import AnalysisEngine
        from .price_tracker import PriceTracker

        engine = AnalysisEngine()
        tracker = PriceTracker.instance()

        sessions = engine.get_history(limit=50, status="completed")
        cutoff = datetime.now() - timedelta(hours=window_hours)

        # Filter by time window
        recent = []
        for s in sessions:
            try:
                created = datetime.fromisoformat(s.created_at)
                if created >= cutoff:
                    recent.append(s)
            except Exception:
                continue

        # Analyze each session's prediction accuracy
        results = []
        for session in recent:
            try:
                # Get current price to compare with prediction
                metrics = tracker.get_metrics_by_address(session.token_address, session.chain)
                current_price = metrics.get("price_usd", 0)

                if session.simulation and current_price > 0:
                    predicted_24h = session.simulation.predicted_price_24h or 0
                    if predicted_24h > 0:
                        prediction_error = abs(current_price - predicted_24h) / predicted_24h * 100
                        # Direction logic: BUY/HOLD is correct if actual price >= entry price
                        # SELL/AVOID is correct if actual price < entry price
                        price_went_up = current_price >= predicted_24h
                        direction_correct = (
                            (price_went_up and session.recommendation in ["BUY", "HOLD"]) or
                            (not price_went_up and session.recommendation in ["SELL", "AVOID"])
                        )
                    else:
                        prediction_error = None
                        direction_correct = None

                    results.append({
                        "session_id": session.session_id,
                        "token_address": session.token_address,
                        "recommendation": session.recommendation,
                        "confidence": session.confidence,
                        "risk_score": session.risk_score,
                        "predicted_price": predicted_24h,
                        "actual_price": current_price,
                        "prediction_error_pct": prediction_error,
                        "direction_correct": direction_correct,
                        "simulation_consensus": session.simulation.consensus_action if session.simulation else None,
                        "on_chain_score": session.on_chain_score,
                        "social_score": session.social_score,
                    })
            except Exception:
                continue

        # Aggregate stats
        correct_directions = [r for r in results if r.get("direction_correct") is True]
        wrong_directions = [r for r in results if r.get("direction_correct") is False]

        # By recommendation type
        by_rec = {}
        for r in results:
            rec = r["recommendation"]
            if rec not in by_rec:
                by_rec[rec] = {"count": 0, "correct": 0, "errors": []}
            by_rec[rec]["count"] += 1
            if r.get("direction_correct"):
                by_rec[rec]["correct"] += 1
            if r.get("prediction_error_pct") is not None:
                by_rec[rec]["errors"].append(r["prediction_error_pct"])

        return {
            "window_hours": window_hours,
            "total_sessions": len(recent),
            "analyzed": len(results),
            "accuracy": {
                "direction_correct": len(correct_directions),
                "direction_wrong": len(wrong_directions),
                "accuracy_rate": len(correct_directions) / max(len(results), 1) * 100,
            },
            "by_recommendation": {
                k: {
                    "count": v["count"],
                    "correct": v["correct"],
                    "accuracy": v["correct"] / max(v["count"], 1) * 100,
                    "avg_error_pct": sum(v["errors"]) / max(len(v["errors"]), 1) if v["errors"] else None,
                }
                for k, v in by_rec.items()
            },
            "results": results[:20],  # Keep top 20 for lesson generation
        }

    def _generate_lessons(self, summary: Dict) -> List[Dict[str, Any]]:
        """Generate lessons from summary - LLM-powered with heuristic fallback"""

        # Try LLM first
        try:
            return self._generate_lessons_llm(summary)
        except Exception as e:
            logger.warning(f"LLM lesson generation failed: {e}, using heuristics")
            return self._generate_lessons_heuristic(summary)

    def _generate_lessons_llm(self, summary: Dict) -> List[Dict[str, Any]]:
        """Use LLM to generate lessons from analysis performance data"""
        prompt = f"""Analyze this trading analysis performance data and generate up to 6 actionable lessons for improving future memecoin analysis.

PERFORMANCE DATA:
- Total sessions analyzed: {summary['total_sessions']}
- Direction accuracy: {summary['accuracy']['accuracy_rate']:.1f}%
- Correct predictions: {summary['accuracy']['direction_correct']}
- Wrong predictions: {summary['accuracy']['direction_wrong']}

BY RECOMMENDATION TYPE:
{json.dumps(summary['by_recommendation'], indent=2)}

SAMPLE RESULTS (recent):
{json.dumps(summary['results'][:10], indent=2, default=str)}

Generate lessons as JSON:
{{
    "lessons": [
        {{"lesson": "short actionable rule for future analysis", "evidence": "specific data supporting this"}},
        ...
    ]
}}

Rules:
- Each lesson must be specific and actionable
- Reference actual data patterns
- Focus on improving accuracy
- Max 6 lessons
- Respond ONLY with valid JSON."""

        response = self.llm.chat(prompt, temperature=0.1)
        parsed = self.llm._parse_json(response)

        lessons = parsed.get("lessons", [])
        return [
            {"lesson": str(l.get("lesson", ""))[:500], "evidence": l.get("evidence", "")}
            for l in lessons if l.get("lesson")
        ][:6]

    def _generate_lessons_heuristic(self, summary: Dict) -> List[Dict[str, Any]]:
        """Fallback: generate lessons from simple heuristics"""
        lessons = []
        acc = summary["accuracy"]
        by_rec = summary["by_recommendation"]

        if acc["accuracy_rate"] < 50:
            lessons.append({
                "lesson": "Overall accuracy below 50%. Be more conservative with BUY recommendations and increase confidence threshold.",
                "evidence": f"Direction accuracy: {acc['accuracy_rate']:.1f}%"
            })

        # Check specific recommendation accuracy
        for rec, data in by_rec.items():
            if data["count"] >= 3 and data["accuracy"] < 40:
                lessons.append({
                    "lesson": f"'{rec}' recommendations have low accuracy ({data['accuracy']:.0f}%). Require higher confidence before issuing '{rec}'.",
                    "evidence": f"{data['correct']}/{data['count']} correct"
                })

        if "AVOID" in by_rec and by_rec["AVOID"].get("accuracy", 0) > 80:
            lessons.append({
                "lesson": "AVOID recommendations are highly accurate. Trust high risk scores and be decisive about flagging dangerous tokens.",
                "evidence": f"AVOID accuracy: {by_rec['AVOID']['accuracy']:.0f}%"
            })

        if not lessons:
            lessons.append({
                "lesson": "Not enough data to derive strong patterns yet. Continue collecting analysis results.",
                "evidence": f"Only {summary['total_sessions']} sessions in window"
            })

        return lessons[:6]

    def _store_learning_run(self, window_hours: int, summary: Dict, lessons: List) -> int:
        """Store a learning run to disk"""
        runs_dir = os.path.join(self.data_dir, 'runs')
        os.makedirs(runs_dir, exist_ok=True)

        run_id = len(os.listdir(runs_dir)) + 1
        run_data = {
            "run_id": run_id,
            "window_hours": window_hours,
            "created_at": datetime.now().isoformat(),
            "summary": summary,
            "lessons": lessons,
        }

        path = os.path.join(runs_dir, f"run_{run_id:04d}.json")
        atomic_write_json(path, run_data)
        return run_id

    def _update_active_lessons(self, lessons: List[Dict]):
        """Update the active lessons file"""
        data = {
            "updated_at": datetime.now().isoformat(),
            "lessons": lessons[:6],
        }
        atomic_write_json(self.lessons_file, data)
