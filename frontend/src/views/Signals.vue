<template>
  <div class="signals-page">
    <header class="page-header">
      <h1>Trading Signals</h1>
      <p class="subtitle">AI-generated alerts from whale activity, sentiment spikes, and price action</p>
    </header>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <button @click="activeTab = 'signals'" :class="{ active: activeTab === 'signals' }">⚡ Signals</button>
      <button @click="activeTab = 'whales'" :class="{ active: activeTab === 'whales' }">🐋 Whale Activity</button>
      <button @click="activeTab = 'smart'" :class="{ active: activeTab === 'smart' }">💎 Smart Money</button>
      <button @click="activeTab = 'new'" :class="{ active: activeTab === 'new' }">🆕 New Pairs</button>
    </div>

    <!-- Signals Tab -->
    <div v-if="activeTab === 'signals'" class="tab-content">
      <div v-if="signals.length" class="signal-grid">
        <div v-for="signal in signals" :key="signal.signal_id" class="signal-card" :class="'border-' + signal.strength">
          <div class="signal-top">
            <span class="signal-type">{{ signal.signal_type.replace(/_/g, ' ') }}</span>
            <span class="signal-strength" :class="'strength-' + signal.strength">{{ signal.strength }}</span>
          </div>
          <h3 class="signal-title">{{ signal.title }}</h3>
          <p class="signal-desc">{{ signal.description }}</p>
          <div class="signal-bottom">
            <span class="signal-token">{{ signal.token_symbol }}</span>
            <span class="signal-time">{{ timeAgo(signal.created_at) }}</span>
          </div>
          <div v-if="signal.action_suggestion" class="signal-suggestion">
            💡 {{ signal.action_suggestion }}
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No active signals</div>
    </div>

    <!-- Whale Activity Tab -->
    <div v-if="activeTab === 'whales'" class="tab-content">
      <div v-if="whaleData.length" class="activity-list">
        <div v-for="(item, idx) in whaleData" :key="idx" class="activity-row">
          <pre class="activity-data">{{ JSON.stringify(item, null, 2) }}</pre>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>Whale tracking active. Configure HELIUS_API_KEY for full monitoring.</p>
      </div>
    </div>

    <!-- Smart Money Tab -->
    <div v-if="activeTab === 'smart'" class="tab-content">
      <div v-if="smartMoney.length" class="activity-list">
        <div v-for="(item, idx) in smartMoney" :key="idx" class="activity-row">
          <pre class="activity-data">{{ JSON.stringify(item, null, 2) }}</pre>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>Smart money tracking active. Add wallet addresses to monitor.</p>
      </div>
    </div>

    <!-- New Pairs Tab -->
    <div v-if="activeTab === 'new'" class="tab-content">
      <div v-if="newPairs.length" class="pairs-grid">
        <div v-for="pair in newPairs" :key="pair.pair_address" class="pair-card">
          <div class="pair-header">
            <span class="pair-symbol">{{ pair.token_symbol }}</span>
            <span class="pair-name">{{ pair.token_name }}</span>
          </div>
          <div class="pair-stats">
            <div><span class="label">Price</span><span class="value">${{ formatPrice(pair.price_usd) }}</span></div>
            <div><span class="label">Liq</span><span class="value">${{ formatLarge(pair.liquidity_usd) }}</span></div>
            <div><span class="label">Vol</span><span class="value">${{ formatLarge(pair.volume_24h) }}</span></div>
            <div>
              <span class="label">24h</span>
              <span class="value" :class="pair.price_change_24h >= 0 ? 'positive' : 'negative'">
                {{ formatChange(pair.price_change_24h) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No new pairs found</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { signalApi } from '../api'

const activeTab = ref('signals')
const signals = ref([])
const whaleData = ref([])
const smartMoney = ref([])
const newPairs = ref([])

const formatPrice = (p) => {
  if (!p) return '0'
  return p < 0.001 ? p.toFixed(8) : p < 1 ? p.toFixed(6) : p.toFixed(4)
}
const formatLarge = (n) => {
  if (!n) return '0'
  return n >= 1e6 ? (n/1e6).toFixed(1)+'M' : n >= 1e3 ? (n/1e3).toFixed(1)+'K' : n.toFixed(0)
}
const formatChange = (c) => c ? ((c >= 0 ? '+' : '') + c.toFixed(1)) : '0.0'
const timeAgo = (d) => {
  if (!d) return ''
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000)
  if (m < 60) return m + 'm ago'
  if (m < 1440) return Math.floor(m/60) + 'h ago'
  return Math.floor(m/1440) + 'd ago'
}

const loadTab = async (tab) => {
  try {
    if (tab === 'signals') {
      const r = await signalApi.list({ limit: 30 })
      signals.value = r.data?.data?.signals || []
    } else if (tab === 'whales') {
      const r = await signalApi.whaleActivity({ limit: 20 })
      whaleData.value = r.data?.data?.activities || []
    } else if (tab === 'smart') {
      const r = await signalApi.smartMoney({ limit: 20 })
      smartMoney.value = r.data?.data?.trades || []
    } else if (tab === 'new') {
      const r = await signalApi.newPairs({ chain: 'solana', limit: 20 })
      newPairs.value = r.data?.data?.pairs || []
    }
  } catch (e) {
    console.error(`Load ${tab} failed:`, e)
  }
}

watch(activeTab, (t) => loadTab(t))
onMounted(() => loadTab('signals'))
</script>

<style scoped>
.signals-page { max-width: 1200px; }
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 28px; font-weight: 600; }
.subtitle { color: var(--text-secondary); font-size: 14px; margin-top: 4px; }

.quick-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.quick-actions button {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 18px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.quick-actions button.active {
  background: rgba(0,255,136,0.08);
  border-color: var(--accent-green);
  color: var(--accent-green);
}
.quick-actions button:hover { background: var(--bg-hover); }

.signal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.signal-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  border-left: 3px solid var(--border);
}
.border-very_strong { border-left-color: var(--accent-green); }
.border-strong { border-left-color: var(--accent-blue); }
.border-moderate { border-left-color: var(--accent-orange); }
.border-weak { border-left-color: var(--text-muted); }

.signal-top { display: flex; justify-content: space-between; margin-bottom: 8px; }
.signal-type { font-size: 10px; color: var(--text-muted); font-family: var(--font-mono); text-transform: uppercase; }
.signal-strength { font-size: 10px; font-family: var(--font-mono); text-transform: uppercase; font-weight: 700; }
.strength-very_strong { color: var(--accent-green); }
.strength-strong { color: var(--accent-blue); }
.strength-moderate { color: var(--accent-orange); }
.strength-weak { color: var(--text-muted); }

.signal-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
.signal-desc { font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px; }
.signal-bottom { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
.signal-token { font-family: var(--font-mono); font-weight: 600; }

.signal-suggestion {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(0,255,136,0.05);
  border-radius: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.pairs-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.pair-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.pair-header { margin-bottom: 12px; }
.pair-symbol { font-family: var(--font-mono); font-weight: 700; font-size: 14px; }
.pair-name { font-size: 11px; color: var(--text-muted); margin-left: 8px; }
.pair-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.pair-stats div { display: flex; justify-content: space-between; }
.pair-stats .label { font-size: 11px; color: var(--text-muted); }
.pair-stats .value { font-size: 12px; font-family: var(--font-mono); }
.positive { color: var(--accent-green); }
.negative { color: var(--accent-red); }

.activity-list { display: flex; flex-direction: column; gap: 8px; }
.activity-row {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
}
.activity-data {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
}

.empty-state { padding: 48px; text-align: center; color: var(--text-muted); font-size: 13px; }
</style>
