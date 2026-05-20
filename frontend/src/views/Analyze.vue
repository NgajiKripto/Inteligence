<template>
  <div class="analyze-page">
    <header class="page-header">
      <h1>Analyze Token</h1>
      <p class="subtitle">AI-powered contract safety, sentiment, and trading simulation</p>
    </header>

    <!-- Input Section -->
    <div class="input-panel">
      <div class="input-group">
        <label>Contract Address</label>
        <input
          v-model="tokenAddress"
          type="text"
          placeholder="Paste token contract address..."
          class="address-input"
          :disabled="analyzing"
        />
      </div>
      <div class="input-row">
        <div class="input-group small">
          <label>Chain</label>
          <select v-model="chain" class="select-input" :disabled="analyzing">
            <option value="solana">Solana</option>
            <option value="ethereum">Ethereum</option>
            <option value="bsc">BSC</option>
          </select>
        </div>
        <div class="input-group small">
          <label>Depth</label>
          <select v-model="depth" class="select-input" :disabled="analyzing">
            <option value="quick">Quick</option>
            <option value="standard">Standard</option>
            <option value="deep">Deep</option>
          </select>
        </div>
        <div class="input-group small">
          <label>Agents</label>
          <select v-model="agentCount" class="select-input" :disabled="analyzing">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
      </div>
      <button @click="startAnalysis" :disabled="!tokenAddress || analyzing" class="analyze-btn">
        <span v-if="!analyzing">◎ Start AI Analysis</span>
        <span v-else>Analyzing... {{ progress }}%</span>
      </button>
    </div>

    <!-- Progress -->
    <div v-if="analyzing" class="progress-panel">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <div class="progress-status">{{ currentStep }}</div>
    </div>

    <!-- Results -->
    <div v-if="result" class="results-panel">
      <!-- Summary Card -->
      <div class="result-header">
        <div class="recommendation" :class="'rec-' + result.recommendation?.toLowerCase()">
          {{ result.recommendation }}
        </div>
        <div class="confidence">
          Confidence: {{ (result.confidence * 100).toFixed(0) }}%
        </div>
      </div>

      <p class="result-summary">{{ result.summary }}</p>

      <!-- Scores -->
      <div class="scores-grid">
        <div class="score-item">
          <div class="score-label">On-Chain Safety</div>
          <div class="score-bar">
            <div class="score-fill green" :style="{ width: session?.on_chain_score + '%' }"></div>
          </div>
          <div class="score-value">{{ session?.on_chain_score || 0 }}/100</div>
        </div>
        <div class="score-item">
          <div class="score-label">Liquidity Health</div>
          <div class="score-bar">
            <div class="score-fill blue" :style="{ width: session?.liquidity_score + '%' }"></div>
          </div>
          <div class="score-value">{{ session?.liquidity_score || 0 }}/100</div>
        </div>
        <div class="score-item">
          <div class="score-label">Social Hype</div>
          <div class="score-bar">
            <div class="score-fill purple" :style="{ width: session?.social_score + '%' }"></div>
          </div>
          <div class="score-value">{{ session?.social_score || 0 }}/100</div>
        </div>
      </div>

      <!-- Findings -->
      <div class="findings-grid">
        <div class="findings-col">
          <h3 class="green-text">Bullish Factors</h3>
          <ul><li v-for="f in result.bullish_factors" :key="f">{{ f }}</li></ul>
        </div>
        <div class="findings-col">
          <h3 class="red-text">Risk Factors</h3>
          <ul><li v-for="f in result.risk_factors" :key="f">{{ f }}</li></ul>
        </div>
      </div>

      <!-- Simulation -->
      <div v-if="result.simulation" class="sim-panel">
        <h3>Multi-Agent Simulation</h3>
        <div class="sim-stats">
          <div class="sim-stat">
            <span class="sim-label">Agents</span>
            <span class="sim-value">{{ result.simulation.total_agents }}</span>
          </div>
          <div class="sim-stat green-text">
            <span class="sim-label">Buy</span>
            <span class="sim-value">{{ result.simulation.buy_percentage }}%</span>
          </div>
          <div class="sim-stat red-text">
            <span class="sim-label">Sell</span>
            <span class="sim-value">{{ result.simulation.sell_percentage }}%</span>
          </div>
          <div class="sim-stat">
            <span class="sim-label">Hold</span>
            <span class="sim-value">{{ result.simulation.hold_percentage }}%</span>
          </div>
          <div class="sim-stat">
            <span class="sim-label">Consensus</span>
            <span class="sim-value" :class="'rec-' + result.simulation.consensus_action?.toLowerCase()">
              {{ result.simulation.consensus_action }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { analysisApi } from '../api'

const route = useRoute()
const tokenAddress = ref('')
const chain = ref('solana')
const depth = ref('standard')
const agentCount = ref(50)
const analyzing = ref(false)
const progress = ref(0)
const currentStep = ref('')
const session = ref(null)
const result = ref(null)

onMounted(() => {
  if (route.query.address) tokenAddress.value = route.query.address
  if (route.query.chain) chain.value = route.query.chain
})

const startAnalysis = async () => {
  if (!tokenAddress.value) return
  analyzing.value = true
  progress.value = 0
  currentStep.value = 'Initializing analysis...'
  result.value = null
  session.value = null

  try {
    const resp = await analysisApi.start({
      token_address: tokenAddress.value,
      chain: chain.value,
      analysis_depth: depth.value,
      simulate: true,
      agent_count: agentCount.value
    })

    const sessionId = resp.data?.data?.session_id
    if (!sessionId) throw new Error('No session ID returned')

    // Poll for progress
    await pollStatus(sessionId)
  } catch (e) {
    console.error('Analysis failed:', e)
    currentStep.value = `Error: ${e.message}`
  } finally {
    analyzing.value = false
  }
}

const pollStatus = async (sessionId) => {
  while (true) {
    await new Promise(r => setTimeout(r, 2000))
    
    try {
      const resp = await analysisApi.status(sessionId)
      const data = resp.data?.data
      
      if (!data) break
      
      session.value = data
      progress.value = data.progress || 0
      currentStep.value = data.current_step || ''
      
      if (data.status === 'completed') {
        // Fetch full report
        const report = await analysisApi.report(sessionId)
        result.value = report.data?.data || {}
        break
      }
      
      if (data.status === 'failed') {
        currentStep.value = `Failed: ${data.error || 'Unknown error'}`
        break
      }
    } catch (e) {
      console.error('Poll error:', e)
      break
    }
  }
}
</script>

<style scoped>
.analyze-page { max-width: 900px; }
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 28px; font-weight: 600; }
.subtitle { color: var(--text-secondary); font-size: 14px; margin-top: 4px; }

.input-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

.input-group { margin-bottom: 16px; }
.input-group label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.address-input {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 14px;
}
.address-input:focus { border-color: var(--accent-green); outline: none; }

.input-row { display: flex; gap: 16px; }
.input-group.small { flex: 1; }

.select-input {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 13px;
}

.analyze-btn {
  width: 100%;
  margin-top: 8px;
  background: var(--accent-green);
  color: #000;
  border: none;
  border-radius: 8px;
  padding: 16px;
  font-size: 15px;
  font-weight: 700;
  font-family: var(--font-mono);
  cursor: pointer;
  transition: opacity 0.2s;
}
.analyze-btn:hover:not(:disabled) { opacity: 0.9; }
.analyze-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.progress-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-primary);
  border-radius: 3px;
  margin-bottom: 12px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent-green);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-status {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.results-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.recommendation {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  padding: 8px 20px;
  border-radius: 8px;
}
.rec-buy { background: rgba(0,255,136,0.15); color: var(--accent-green); border: 1px solid rgba(0,255,136,0.3); }
.rec-sell { background: rgba(255,68,102,0.15); color: var(--accent-red); border: 1px solid rgba(255,68,102,0.3); }
.rec-hold { background: rgba(136,136,170,0.15); color: var(--text-secondary); border: 1px solid var(--border); }
.rec-avoid { background: rgba(255,0,68,0.15); color: #ff0044; border: 1px solid rgba(255,0,68,0.3); }

.confidence { font-size: 13px; color: var(--text-muted); font-family: var(--font-mono); }

.result-summary { font-size: 14px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 24px; }

.scores-grid { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.score-item { display: grid; grid-template-columns: 140px 1fr 60px; align-items: center; gap: 12px; }
.score-label { font-size: 12px; color: var(--text-muted); }
.score-bar { height: 8px; background: var(--bg-primary); border-radius: 4px; overflow: hidden; }
.score-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
.score-fill.green { background: var(--accent-green); }
.score-fill.blue { background: var(--accent-blue); }
.score-fill.purple { background: var(--accent-purple); }
.score-value { font-size: 12px; font-family: var(--font-mono); color: var(--text-secondary); text-align: right; }

.findings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
.findings-col h3 { font-size: 13px; margin-bottom: 8px; }
.green-text { color: var(--accent-green); }
.red-text { color: var(--accent-red); }
.findings-col ul { list-style: none; padding: 0; }
.findings-col li { font-size: 12px; color: var(--text-secondary); padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }

.sim-panel {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 20px;
}
.sim-panel h3 { font-size: 14px; margin-bottom: 16px; }
.sim-stats { display: flex; gap: 24px; flex-wrap: wrap; }
.sim-stat { text-align: center; }
.sim-label { display: block; font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.sim-value { font-size: 18px; font-weight: 700; font-family: var(--font-mono); }
</style>
