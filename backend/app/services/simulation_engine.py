"""
Simulation Engine - Multi-agent trading simulation for memecoins
Creates diverse AI trader agents that interact and make decisions
based on market data, sentiment, and social signals
"""

import json
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..config import Config
from ..models.analysis import AgentProfile, SimulationResult
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('memecoin.services.simulation')


# Agent persona templates
AGENT_PERSONAS = [
    {"persona": "degen_trader", "risk_appetite": 0.9, "strategy": "momentum", "bias": "bullish"},
    {"persona": "whale", "risk_appetite": 0.6, "capital_usd": 100000, "strategy": "accumulate", "bias": "neutral"},
    {"persona": "paper_hands", "risk_appetite": 0.3, "strategy": "quick_flip", "bias": "neutral"},
    {"persona": "diamond_hands", "risk_appetite": 0.7, "strategy": "holder", "bias": "bullish"},
    {"persona": "sniper_bot", "risk_appetite": 0.95, "strategy": "sniper", "bias": "neutral"},
    {"persona": "conservative_trader", "risk_appetite": 0.2, "strategy": "safe_only", "bias": "bearish"},
    {"persona": "influencer", "risk_appetite": 0.7, "twitter_influence": 50000, "strategy": "narrative", "bias": "bullish"},
    {"persona": "technical_analyst", "risk_appetite": 0.5, "strategy": "technical", "bias": "neutral"},
    {"persona": "contrarian", "risk_appetite": 0.6, "strategy": "contrarian", "bias": "neutral"},
    {"persona": "fomo_buyer", "risk_appetite": 0.8, "strategy": "fomo", "bias": "bullish"},
    {"persona": "smart_money", "risk_appetite": 0.5, "capital_usd": 50000, "strategy": "informed", "bias": "neutral"},
    {"persona": "bot_trader", "risk_appetite": 0.7, "strategy": "algorithmic", "bias": "neutral"},
]


class SimulationEngine:
    """
    Multi-agent simulation engine for memecoin trading prediction
    
    Creates a virtual market with diverse AI agents that:
    1. Receive the same market data
    2. Make independent buy/sell/hold decisions
    3. Interact via simulated social media
    4. Evolve their positions over multiple rounds
    """
    
    def __init__(self):
        self.llm = LLMClient()
    
    def run_simulation(self, token_address: str, chain: str = "solana",
                       agent_count: int = 50, rounds: int = 10,
                       scenario: str = "neutral",
                       inject_event: str = "") -> SimulationResult:
        """
        Run a complete multi-agent trading simulation
        
        Args:
            token_address: Token contract address
            chain: Blockchain
            agent_count: Number of AI agents
            rounds: Simulation rounds
            scenario: Market scenario (bullish/neutral/bearish/crash)
            inject_event: Optional event to inject mid-simulation
        
        Returns:
            SimulationResult with predictions and analysis
        """
        logger.info(f"Starting simulation: {token_address}, {agent_count} agents, {rounds} rounds")
        
        # 1. Gather market context
        market_context = self._gather_market_context(token_address, chain)
        
        # 2. Create agent profiles
        agents = self._create_agents(agent_count)
        
        # 3. Run simulation rounds
        sentiment_timeline = []
        all_actions = []
        
        for round_num in range(1, rounds + 1):
            logger.info(f"Simulation round {round_num}/{rounds}")
            
            # Inject event mid-simulation if provided
            event_context = ""
            if inject_event and round_num == rounds // 2:
                event_context = f"\n\nBREAKING EVENT: {inject_event}"
            
            # Get agent decisions for this round
            round_actions = self._run_round(
                agents=agents,
                market_context=market_context,
                scenario=scenario,
                round_num=round_num,
                total_rounds=rounds,
                event_context=event_context,
                previous_actions=all_actions[-3:] if all_actions else []
            )
            
            all_actions.append(round_actions)
            
            # Track sentiment evolution
            buy_count = sum(1 for a in round_actions if a["action"] == "BUY")
            sell_count = sum(1 for a in round_actions if a["action"] == "SELL")
            hold_count = sum(1 for a in round_actions if a["action"] == "HOLD")
            total = len(round_actions)
            
            sentiment_timeline.append({
                "round": round_num,
                "buy_pct": buy_count / total * 100 if total else 0,
                "sell_pct": sell_count / total * 100 if total else 0,
                "hold_pct": hold_count / total * 100 if total else 0,
                "sentiment_score": (buy_count - sell_count) / total if total else 0
            })
        
        # 4. Aggregate results
        result = self._aggregate_results(
            agents=agents,
            all_actions=all_actions,
            sentiment_timeline=sentiment_timeline,
            rounds_completed=rounds,
            market_context=market_context
        )
        
        logger.info(f"Simulation complete: consensus={result.consensus_action}, confidence={result.consensus_strength}")
        
        return result
    
    def _gather_market_context(self, token_address: str, chain: str) -> Dict[str, Any]:
        """Gather current market data for the simulation"""
        from .price_tracker import PriceTracker
        from .onchain_analyzer import OnChainAnalyzer
        
        tracker = PriceTracker()
        onchain = OnChainAnalyzer()
        
        metrics = tracker.get_metrics_by_address(token_address, chain)
        buy_sell = tracker.get_buy_sell_ratio(token_address, chain)
        
        return {
            "token_address": token_address,
            "chain": chain,
            "price_usd": metrics.get("price_usd", 0),
            "price_change_24h": metrics.get("price_change", {}).get("24h", 0),
            "volume_24h": metrics.get("volume", {}).get("24h", 0),
            "liquidity_usd": metrics.get("liquidity_usd", 0),
            "market_cap": metrics.get("market_cap", 0),
            "buy_sell_ratio": buy_sell,
        }
    
    def _create_agents(self, count: int) -> List[AgentProfile]:
        """Create diverse agent profiles for simulation"""
        agents = []
        
        for i in range(count):
            # Pick a base persona (cycle through templates)
            base = AGENT_PERSONAS[i % len(AGENT_PERSONAS)].copy()
            
            # Add randomization
            agent = AgentProfile(
                persona=base["persona"],
                risk_appetite=min(1.0, max(0.0, base.get("risk_appetite", 0.5) + random.uniform(-0.1, 0.1))),
                capital_usd=base.get("capital_usd", random.choice([500, 1000, 2000, 5000, 10000])),
                experience_level=random.choice(["beginner", "intermediate", "advanced", "expert"]),
                bias=base.get("bias", "neutral"),
                twitter_influence=base.get("twitter_influence", random.randint(0, 10000)),
                strategy=base.get("strategy", "mixed"),
            )
            agents.append(agent)
        
        return agents
    
    def _run_round(self, agents: List[AgentProfile], market_context: Dict,
                   scenario: str, round_num: int, total_rounds: int,
                   event_context: str = "",
                   previous_actions: List = None) -> List[Dict[str, Any]]:
        """
        Run one simulation round - each agent makes a decision
        Uses LLM to generate diverse, realistic agent responses
        """
        # Build context for agents
        price = market_context.get("price_usd", 0)
        change_24h = market_context.get("price_change_24h", 0)
        volume = market_context.get("volume_24h", 0)
        liquidity = market_context.get("liquidity_usd", 0)
        
        # Batch agents into groups for efficiency
        batch_size = min(10, len(agents))
        actions = []
        
        for batch_start in range(0, len(agents), batch_size):
            batch = agents[batch_start:batch_start + batch_size]
            
            agent_descriptions = "\n".join([
                f"Agent {i+1}: {a.persona} (risk={a.risk_appetite:.1f}, capital=${a.capital_usd:,.0f}, strategy={a.strategy}, bias={a.bias})"
                for i, a in enumerate(batch)
            ])
            
            prev_context = ""
            if previous_actions:
                last_round = previous_actions[-1] if previous_actions else []
                buy_pct = sum(1 for a in last_round if a.get("action") == "BUY") / max(len(last_round), 1) * 100
                prev_context = f"\nPrevious round: {buy_pct:.0f}% bought, {100-buy_pct:.0f}% sold/held"
            
            prompt = f"""You are simulating a memecoin trading market. Round {round_num}/{total_rounds}.

MARKET DATA:
- Price: ${price}
- 24h Change: {change_24h:+.1f}%
- 24h Volume: ${volume:,.0f}
- Liquidity: ${liquidity:,.0f}
- Scenario: {scenario}
{event_context}
{prev_context}

AGENTS:
{agent_descriptions}

For EACH agent, decide their action based on their persona, risk appetite, and strategy.
Each agent must choose: BUY, SELL, or HOLD.

Respond with a JSON array like:
[
  {{"agent": 1, "action": "BUY", "reason": "brief reason", "conviction": 0.8}},
  {{"agent": 2, "action": "SELL", "reason": "brief reason", "conviction": 0.6}},
  ...
]

Consider each agent's unique personality. A degen would buy aggressively. Paper hands would sell on any dip. Contrarians go against the crowd. Be realistic and diverse.

Respond ONLY with the JSON array."""

            try:
                response = self.llm.chat(prompt, temperature=Config.AGENT_TEMPERATURE)
                
                # Parse response
                try:
                    batch_actions = json.loads(response)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown
                    if "```json" in response:
                        json_str = response.split("```json")[1].split("```")[0].strip()
                        batch_actions = json.loads(json_str)
                    elif "```" in response:
                        json_str = response.split("```")[1].split("```")[0].strip()
                        batch_actions = json.loads(json_str)
                    else:
                        # Fallback: random actions
                        batch_actions = [
                            {"agent": i+1, "action": random.choice(["BUY", "SELL", "HOLD"]),
                             "reason": "LLM parse failed", "conviction": 0.5}
                            for i in range(len(batch))
                        ]
                
                # Map actions to agent profiles
                for i, action_data in enumerate(batch_actions):
                    if i < len(batch):
                        action_data["persona"] = batch[i].persona
                        action_data["strategy"] = batch[i].strategy
                        actions.append(action_data)
                        
            except Exception as e:
                logger.error(f"Simulation round failed for batch: {e}")
                # Fallback actions
                for i, agent in enumerate(batch):
                    actions.append({
                        "agent": batch_start + i + 1,
                        "action": random.choice(["BUY", "SELL", "HOLD"]),
                        "reason": "Simulation error fallback",
                        "conviction": 0.5,
                        "persona": agent.persona
                    })
        
        return actions
    
    def _aggregate_results(self, agents: List[AgentProfile], all_actions: List,
                           sentiment_timeline: List, rounds_completed: int,
                           market_context: Dict) -> SimulationResult:
        """Aggregate all simulation rounds into a final result"""
        
        # Count final round actions
        final_actions = all_actions[-1] if all_actions else []
        total = len(final_actions)
        
        buy_count = sum(1 for a in final_actions if a.get("action") == "BUY")
        sell_count = sum(1 for a in final_actions if a.get("action") == "SELL")
        hold_count = sum(1 for a in final_actions if a.get("action") == "HOLD")
        
        buy_pct = buy_count / total * 100 if total else 0
        sell_pct = sell_count / total * 100 if total else 0
        hold_pct = hold_count / total * 100 if total else 0
        
        # Determine consensus
        if buy_pct > 60:
            consensus = "BUY"
            strength = buy_pct / 100
        elif sell_pct > 60:
            consensus = "SELL"
            strength = sell_pct / 100
        elif buy_pct > sell_pct + 15:
            consensus = "BUY"
            strength = (buy_pct - sell_pct) / 100
        elif sell_pct > buy_pct + 15:
            consensus = "SELL"
            strength = (sell_pct - buy_pct) / 100
        else:
            consensus = "HOLD"
            strength = hold_pct / 100
        
        # Find notable actions (high conviction)
        notable = []
        for round_actions in all_actions:
            for action in round_actions:
                if action.get("conviction", 0) >= 0.8:
                    notable.append({
                        "persona": action.get("persona", ""),
                        "action": action.get("action", ""),
                        "reason": action.get("reason", ""),
                        "conviction": action.get("conviction", 0)
                    })
        
        # Price prediction based on consensus
        current_price = market_context.get("price_usd", 0)
        if consensus == "BUY":
            predicted_1h = current_price * (1 + strength * 0.05)
            predicted_24h = current_price * (1 + strength * 0.15)
        elif consensus == "SELL":
            predicted_1h = current_price * (1 - strength * 0.05)
            predicted_24h = current_price * (1 - strength * 0.15)
        else:
            predicted_1h = current_price
            predicted_24h = current_price * (1 + random.uniform(-0.03, 0.03))
        
        return SimulationResult(
            total_agents=len(agents),
            rounds_completed=rounds_completed,
            buy_percentage=round(buy_pct, 1),
            sell_percentage=round(sell_pct, 1),
            hold_percentage=round(hold_pct, 1),
            predicted_price_1h=round(predicted_1h, 8),
            predicted_price_24h=round(predicted_24h, 8),
            price_confidence=round(strength, 2),
            sentiment_timeline=sentiment_timeline,
            notable_actions=notable[:10],
            consensus_action=consensus,
            consensus_strength=round(strength, 2)
        )
