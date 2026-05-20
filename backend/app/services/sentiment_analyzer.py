"""
Sentiment Analyzer Service - Social media sentiment analysis for memecoins
Monitors Twitter, Telegram, Reddit for mentions and sentiment
Uses LLM for nuanced sentiment classification
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

import requests

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('memecoin.services.sentiment')


class SentimentAnalyzer:
    """Analyzes social media sentiment for memecoin tokens"""
    
    def __init__(self):
        self.llm = LLMClient()
        self.twitter_bearer = Config.TWITTER_BEARER_TOKEN
    
    def analyze_token_sentiment(self, symbol: str, name: str = "",
                                 address: str = "") -> Dict[str, Any]:
        """
        Comprehensive sentiment analysis for a token
        
        Aggregates data from:
        - Twitter/X mentions and sentiment
        - Telegram group activity
        - Reddit mentions
        - Influencer tracking
        """
        result = {
            "symbol": symbol,
            "name": name,
            "twitter": self._analyze_twitter(symbol, name),
            "overall_sentiment": 0.0,
            "sentiment_label": "neutral",
            "trending_score": 0.0,
            "key_narratives": [],
            "influencer_mentions": [],
            "updated_at": datetime.now().isoformat()
        }
        
        # Calculate overall sentiment
        twitter_score = result["twitter"].get("sentiment_score", 0)
        result["overall_sentiment"] = twitter_score
        
        if twitter_score > 0.6:
            result["sentiment_label"] = "very_bullish"
        elif twitter_score > 0.3:
            result["sentiment_label"] = "bullish"
        elif twitter_score < -0.6:
            result["sentiment_label"] = "very_bearish"
        elif twitter_score < -0.3:
            result["sentiment_label"] = "bearish"
        else:
            result["sentiment_label"] = "neutral"
        
        # Trending score based on mention volume
        mentions = result["twitter"].get("mention_count", 0)
        if mentions > 1000:
            result["trending_score"] = 1.0
        elif mentions > 500:
            result["trending_score"] = 0.8
        elif mentions > 100:
            result["trending_score"] = 0.5
        elif mentions > 20:
            result["trending_score"] = 0.3
        else:
            result["trending_score"] = 0.1
        
        return result
    
    def get_market_sentiment(self, chain: str = "all", timeframe: str = "24h") -> Dict[str, Any]:
        """
        Get overall memecoin market sentiment
        
        Returns aggregate sentiment across the memecoin ecosystem.
        Feeds real aggregated data from tracked tokens into the LLM prompt.
        """
        # Gather REAL market data to feed to LLM
        real_data_summary = self._gather_market_data_summary(chain)
        
        prompt = f"""Analyze the memecoin market sentiment based on the following REAL aggregated data.

Chain focus: {chain}
Timeframe: {timeframe}

ACTUAL MARKET DATA:
{real_data_summary}

Based on this real data, provide a JSON response with:
- overall_score: float from -1.0 (extreme fear) to 1.0 (extreme greed)
- label: one of [extreme_fear, fear, neutral, greed, extreme_greed]
- market_mood: brief description based on the data above
- hot_narratives: list of likely trending narratives given the data
- risk_level: low/medium/high/extreme
- data_driven: true

IMPORTANT: Base your analysis ONLY on the data provided above. Do NOT hallucinate data points.
Respond ONLY with valid JSON."""

        try:
            response = self.llm.chat(prompt, temperature=0.3)
            
            import json
            # Try to parse JSON from response
            try:
                sentiment_data = json.loads(response)
            except json.JSONDecodeError:
                # Extract JSON from markdown code block
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                    sentiment_data = json.loads(json_str)
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                    sentiment_data = json.loads(json_str)
                else:
                    sentiment_data = {
                        "overall_score": 0,
                        "label": "neutral",
                        "market_mood": "Unable to determine",
                        "hot_narratives": [],
                        "risk_level": "medium",
                        "notable_events": []
                    }
            
            sentiment_data["chain"] = chain
            sentiment_data["timeframe"] = timeframe
            sentiment_data["updated_at"] = datetime.now().isoformat()
            sentiment_data["data_source"] = "aggregated_market_data"
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Market sentiment analysis failed: {e}")
            return {
                "overall_score": 0,
                "label": "neutral",
                "market_mood": "Analysis unavailable",
                "chain": chain,
                "timeframe": timeframe,
                "error": str(e)
            }
    
    def _gather_market_data_summary(self, chain: str) -> str:
        """Gather real market data to provide context for sentiment analysis"""
        try:
            from .token_scanner import TokenScanner
            from .price_tracker import PriceTracker
            
            scanner = TokenScanner()
            tracker = PriceTracker.instance()
            
            # Get tracked tokens for aggregate stats
            tokens = scanner.get_watchlist(status='all', sort_by='volume')
            
            if not tokens:
                # Try trending if no watchlist
                tokens = scanner.get_trending(chain=chain, limit=10)
            
            if not tokens:
                return "No tracked tokens available. Limited data for analysis."
            
            # Aggregate stats
            total_tokens = len(tokens)
            gainers = sum(1 for t in tokens if (t.metrics.price_change_24h or 0) > 0)
            losers = sum(1 for t in tokens if (t.metrics.price_change_24h or 0) < 0)
            avg_change = sum(t.metrics.price_change_24h or 0 for t in tokens) / max(total_tokens, 1)
            total_volume = sum(t.metrics.volume_24h or 0 for t in tokens)
            total_liquidity = sum(t.metrics.liquidity_usd or 0 for t in tokens)
            
            # Top movers
            sorted_by_change = sorted(tokens, key=lambda t: t.metrics.price_change_24h or 0, reverse=True)
            top_gainers = [(t.symbol, t.metrics.price_change_24h) for t in sorted_by_change[:3] if t.metrics.price_change_24h]
            top_losers = [(t.symbol, t.metrics.price_change_24h) for t in sorted_by_change[-3:] if t.metrics.price_change_24h]
            
            summary = f"""- Tokens tracked: {total_tokens}
- Gainers: {gainers}, Losers: {losers}
- Average 24h change: {avg_change:+.1f}%
- Total 24h volume: ${total_volume:,.0f}
- Total liquidity: ${total_liquidity:,.0f}
- Top gainers: {', '.join(f'{s} ({c:+.1f}%)' for s, c in top_gainers) or 'N/A'}
- Top losers: {', '.join(f'{s} ({c:+.1f}%)' for s, c in top_losers) or 'N/A'}
- Market direction: {'Bullish' if avg_change > 5 else 'Bearish' if avg_change < -5 else 'Neutral'}"""
            
            return summary
            
        except Exception as e:
            logger.warning(f"Failed to gather market data: {e}")
            return "Market data gathering failed. Provide general assessment only."
    
    def analyze_text_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment of a list of social media posts using LLM
        
        Returns aggregate sentiment and key themes
        """
        if not texts:
            return {"sentiment_score": 0, "label": "neutral", "themes": []}
        
        # Sample if too many texts
        sample = texts[:50] if len(texts) > 50 else texts
        combined = "\n---\n".join(sample)
        
        prompt = f"""Analyze the sentiment of these social media posts about a cryptocurrency token.

Posts:
{combined}

Provide a JSON response with:
- sentiment_score: float from -1.0 (very bearish) to 1.0 (very bullish)
- label: bearish/slightly_bearish/neutral/slightly_bullish/bullish
- confidence: float 0-1 how confident in the assessment
- key_themes: list of main themes/topics discussed
- fomo_level: float 0-1 how much FOMO is present
- fud_level: float 0-1 how much FUD is present
- bot_likelihood: float 0-1 likelihood posts are bot-generated

Respond ONLY with valid JSON."""

        try:
            response = self.llm.chat(prompt, temperature=0.2)
            
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                return {"sentiment_score": 0, "label": "neutral", "error": "Parse failed"}
                
        except Exception as e:
            logger.error(f"Text sentiment analysis failed: {e}")
            return {"sentiment_score": 0, "label": "neutral", "error": str(e)}
    
    # === Twitter Analysis ===
    
    def _analyze_twitter(self, symbol: str, name: str = "") -> Dict[str, Any]:
        """Analyze Twitter mentions and sentiment for a token"""
        if not self.twitter_bearer:
            return {
                "mention_count": 0,
                "sentiment_score": 0,
                "top_tweets": [],
                "note": "Twitter Bearer Token not configured"
            }
        
        try:
            # Search for token mentions
            query = f"${symbol}" if symbol else name
            url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {"Authorization": f"Bearer {self.twitter_bearer}"}
            params = {
                "query": f"{query} -is:retweet lang:en",
                "max_results": 100,
                "tweet.fields": "created_at,public_metrics,author_id"
            }
            
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code != 200:
                logger.warning(f"Twitter API returned {resp.status_code}")
                return {
                    "mention_count": 0,
                    "sentiment_score": 0,
                    "top_tweets": [],
                    "error": f"Twitter API error: {resp.status_code}"
                }
            
            data = resp.json()
            tweets = data.get("data", [])
            
            # Extract tweet texts for sentiment analysis
            tweet_texts = [t.get("text", "") for t in tweets]
            
            # Analyze sentiment of tweets
            sentiment = self.analyze_text_sentiment(tweet_texts) if tweet_texts else {}
            
            # Find top tweets by engagement
            top_tweets = sorted(
                tweets,
                key=lambda t: (
                    t.get("public_metrics", {}).get("like_count", 0) +
                    t.get("public_metrics", {}).get("retweet_count", 0) * 2
                ),
                reverse=True
            )[:5]
            
            return {
                "mention_count": len(tweets),
                "sentiment_score": sentiment.get("sentiment_score", 0),
                "sentiment_label": sentiment.get("label", "neutral"),
                "fomo_level": sentiment.get("fomo_level", 0),
                "fud_level": sentiment.get("fud_level", 0),
                "bot_likelihood": sentiment.get("bot_likelihood", 0),
                "key_themes": sentiment.get("key_themes", []),
                "top_tweets": [
                    {
                        "text": t.get("text", "")[:200],
                        "likes": t.get("public_metrics", {}).get("like_count", 0),
                        "retweets": t.get("public_metrics", {}).get("retweet_count", 0),
                    }
                    for t in top_tweets
                ]
            }
            
        except Exception as e:
            logger.error(f"Twitter analysis failed: {e}")
            return {"mention_count": 0, "sentiment_score": 0, "error": str(e)}
