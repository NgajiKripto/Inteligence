# MemeCoin Intelligence

**AI-powered memecoin trading analysis platform with multi-agent simulation**

MemeCoin Intelligence is a comprehensive platform that helps traders analyze memecoins using artificial intelligence. It combines on-chain contract analysis, social sentiment tracking, whale monitoring, and multi-agent trading simulations to generate actionable trading insights.

## Features

### On-Chain Analysis
- Smart contract safety checks (mint authority, freeze, honeypot detection)
- Holder distribution and whale concentration analysis
- LP lock verification
- Rug-pull risk scoring

### Social Sentiment
- Twitter/X mention tracking and sentiment analysis
- Trending score calculation
- Influencer mention detection
- FOMO/FUD level assessment (via LLM)

### Whale & Smart Money Tracking
- Large transaction monitoring
- Smart money wallet tracking
- Accumulation/distribution pattern detection
- Real-time whale alerts

### Multi-Agent Trading Simulation
- 12 diverse AI trader personas (degen, whale, paper hands, sniper, etc.)
- LLM-powered decision making per agent
- Configurable scenarios (bullish/bearish/neutral/crash)
- Event injection mid-simulation
- Consensus prediction with confidence scoring

### AI Analyst Chat
- Conversational AI with full context access
- Ask about any token, risk, or strategy
- Integrates all collected data sources

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, Flask, Pydantic |
| Frontend | Vue.js 3, Vite, Chart.js |
| LLM | OpenAI SDK (supports GPT-4, DeepSeek, Qwen, etc.) |
| On-Chain | Helius (Solana), DexScreener, Birdeye |
| Social | Twitter API v2 |
| Deployment | Docker, GitHub Actions |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An OpenAI-compatible API key

### 1. Clone & Configure

```bash
git clone https://github.com/NgajiKripto/Inteligence.git
cd Inteligence
cp .env.example .env
# Edit .env with your API keys
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Backend runs on `http://localhost:5001`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`

### 4. Docker (Alternative)

```bash
docker-compose up -d
```

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | OpenAI or compatible API key |
| `LLM_BASE_URL` | No | API endpoint (default: OpenAI) |
| `LLM_MODEL_NAME` | No | Model to use (default: gpt-4o-mini) |
| `HELIUS_API_KEY` | Recommended | Solana on-chain analysis |
| `TWITTER_BEARER_TOKEN` | Optional | Social sentiment tracking |
| `BIRDEYE_API_KEY` | Optional | Price history data |

## API Endpoints

### Token Management
- `POST /api/token/discover` — Discover & track a new token
- `GET /api/token/trending` — Get trending memecoins
- `GET /api/token/watchlist` — Get tracked tokens
- `GET /api/token/<id>/risk` — Get risk assessment

### Analysis
- `POST /api/analysis/start` — Start full AI analysis pipeline
- `GET /api/analysis/status/<id>` — Check analysis progress
- `GET /api/analysis/report/<id>` — Get completed report
- `POST /api/analysis/simulate` — Run trading simulation
- `POST /api/analysis/chat` — Chat with AI analyst

### Signals
- `GET /api/signal/list` — Get active trading signals
- `GET /api/signal/whale-activity` — Recent whale movements
- `GET /api/signal/smart-money` — Smart money trades
- `GET /api/signal/new-pairs` — Newly created pairs
- `GET /api/signal/rug-check/<address>` — Quick rug check

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vue.js 3)                    │
│  Dashboard │ Trending │ Analyze │ Signals │ AI Chat     │
└────────────────────────────┬────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────┐
│                    Backend (Flask)                        │
│                                                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────────┐ │
│  │  Token   │  │ Analysis  │  │      Signal          │ │
│  │   API    │  │    API    │  │       API            │ │
│  └────┬─────┘  └─────┬─────┘  └──────────┬──────────┘ │
│       │               │                    │            │
│  ┌────┴───────────────┴────────────────────┴─────────┐ │
│  │              Core Services                         │ │
│  │                                                    │ │
│  │  TokenScanner │ PriceTracker │ OnChainAnalyzer    │ │
│  │  SentimentAnalyzer │ WhaleTracker │ RiskAssessor  │ │
│  │  SimulationEngine │ SignalGenerator │ AnalystAgent │ │
│  │  AnalysisEngine (orchestrator)                    │ │
│  └───────────────────────────────────────────────────┘ │
│                          │                              │
│  ┌───────────────────────┴───────────────────────────┐ │
│  │           External Integrations                    │ │
│  │  DexScreener │ Helius │ Birdeye │ Twitter │ LLM  │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # REST API endpoints
│   │   ├── models/       # Pydantic data models
│   │   ├── services/     # Core business logic
│   │   └── utils/        # LLM client, logger, retry
│   ├── requirements.txt
│   └── run.py            # Entry point
├── frontend/
│   ├── src/
│   │   ├── api/          # API client
│   │   ├── components/   # Vue components
│   │   ├── views/        # Page views
│   │   └── router/       # Vue Router
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Risk Disclaimer

This tool is for research and educational purposes only. Memecoin trading is extremely risky. Never invest more than you can afford to lose. The AI predictions and simulations are not financial advice.

## License

MIT
