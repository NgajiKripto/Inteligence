<template>
  <div class="dashboard">
    <header class="page-header">
      <h1>Dashboard</h1>
      <p class="subtitle">Real-time memecoin market overview</p>
    </header>

    <!-- Quick Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Tracked Tokens</div>
        <div class="stat-value">{{ watchlist.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Active Signals</div>
        <div class="stat-value accent-orange">{{ signals.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Market Sentiment</div>
        <div class="stat-value" :class="sentimentClass">{{ sentimentLabel }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Analyses Run</div>
        <div class="stat-value">{{ analysisCount }}</div>
      </div>
    </div>

    <!-- Two Column Layout -->
    <div class="dashboard-grid">
      <!-- Watchlist -->
      <section class="panel">
        <div class="panel-header">
          <h2>Watchlist</h2>
          <router-link to="/analyze" class="btn-sm">+ Add Token</router-link>
        </div>
        <div class="token-list" v-if="watchlist.length">
          <div class="token-row" v-for="token in watchlist" :key="token.token_id">
            <div class="token-info">
              <span class="token-symbol">{{ token.symbol }}</span>
              <span class="token-chain">{{ token.chain }}</span>
            </div>
            <div class="token-price">${{ formatPrice(token.metrics?.price_usd) }}</div>
            <div class="token-change" :class="token.metrics?.price_change_24h >= 0 ? 'positive' : 'negative'">
              {{ formatChange(token.metrics?.price_change_24h) }}%
            </div>
            <div class="token-risk" :class="'risk-' + token.risk_level">
              {{ token.risk_level || '—' }}
            </div>
          </div>
        </div>
        <div class="empty-state" v-else>
          <p>No tokens tracked yet</p>
          <router-link to="/analyze" class="btn-sm">Discover Tokens</router-link>
        </div>
      </section>

      <!-- Recent Signals -->
      <section class="panel">
        <div class="panel-header">
          <h2>Recent Signals</h2>
          <router-link to="/signals" class="btn-sm">View All</router-link>
        </div>
        <div class="signal-list" v-if="signals.length">
          <div class="signal-row" v-for="signal in signals.slice(0, 8)" :key="signal.signal_id">
            <div class="signal-icon" :class="'signal-' + signal.strength">⚡</div>
            <div class="signal-info">
              <div class="signal-title">{{ signal.title }}</div>
              <div class="signal-meta">{{ signal.token_symbol }} · {{ signal.signal_type }}</div>
            </div>
            <div class="signal-time">{{ timeAgo(signal.created_at) }}</div>
          </div>
        </div>
        <div class="empty-state" v-else>
          <p>No signals yet. Start tracking tokens to receive alerts.</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tokenApi, signalApi, analysisApi } from '../api'

const watchlist = ref([])
const signals = ref([])
const sentiment = ref({})
const analysisCount = ref(0)

const sentimentLabel = computed(() => {
  const label = sentiment.value?.label || 'neutral'
  return label.replace('_', ' ')
})

const sentimentClass = computed(() => {
  const score = sentiment.value?.overall_score || 0
  if (score > 0.3) return 'accent-green'
  if (score < -0.3) return 'accent-red'
  return ''
})

const formatPrice = (price) => {
  if (!price) return '0.00'
  if (price < 0.001) return price.toFixed(8)
  if (price < 1) return price.toFixed(6)
  return price.toFixed(4)
}

const formatChange = (change) => {
  if (!change) return '0.0'
  return (change >= 0 ? '+' : '') + change.toFixed(1)
}

const timeAgo = (dateStr) => {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  return `${Math.floor(hrs / 24)}d`
}

onMounted(async () => {
  try {
    const [wl, sig, sent, hist] = await Promise.allSettled([
      tokenApi.watchlist(),
      signalApi.list({ limit: 10 }),
      signalApi.sentiment(),
      analysisApi.history({ limit: 100 })
    ])
    
    if (wl.status === 'fulfilled') watchlist.value = wl.value.data?.data?.tokens || []
    if (sig.status === 'fulfilled') signals.value = sig.value.data?.data?.signals || []
    if (sent.status === 'fulfilled') sentiment.value = sent.value.data?.data || {}
    if (hist.status === 'fulfilled') analysisCount.value = hist.value.data?.data?.count || 0
  } catch (e) {
    console.error('Dashboard load error:', e)
  }
})
</script>

<style scoped>
.dashboard { max-width: 1200px; }

.page-header {
  margin-bottom: 32px;
}
.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 4px;
}
.subtitle {
  color: var(--text-secondary);
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.accent-green { color: var(--accent-green); }
.accent-red { color: var(--accent-red); }
.accent-orange { color: var(--accent-orange); }

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h2 {
  font-size: 16px;
  font-weight: 600;
}

.btn-sm {
  font-size: 12px;
  padding: 6px 12px;
  background: var(--bg-hover);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  text-decoration: none;
}
.btn-sm:hover { color: var(--accent-green); border-color: var(--accent-green); text-decoration: none; }

.token-list, .signal-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.token-row {
  display: grid;
  grid-template-columns: 1.5fr 1fr 0.8fr 0.7fr;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  background: var(--bg-secondary);
  font-size: 13px;
}

.token-symbol {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-primary);
}

.token-chain {
  font-size: 10px;
  color: var(--text-muted);
  margin-left: 8px;
  text-transform: uppercase;
}

.token-price {
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.token-change {
  font-family: var(--font-mono);
  font-weight: 600;
}
.token-change.positive { color: var(--accent-green); }
.token-change.negative { color: var(--accent-red); }

.token-risk {
  font-size: 11px;
  font-family: var(--font-mono);
  text-transform: uppercase;
  text-align: right;
}
.risk-low { color: var(--accent-green); }
.risk-medium { color: var(--accent-orange); }
.risk-high { color: var(--accent-red); }
.risk-critical { color: #ff0044; font-weight: 700; }

.signal-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  background: var(--bg-secondary);
}

.signal-icon {
  font-size: 14px;
}
.signal-strong, .signal-very_strong { color: var(--accent-green); }
.signal-moderate { color: var(--accent-orange); }
.signal-weak { color: var(--text-muted); }

.signal-info { flex: 1; }
.signal-title { font-size: 13px; font-weight: 500; }
.signal-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.signal-time { font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); }

.empty-state {
  text-align: center;
  padding: 32px;
  color: var(--text-muted);
  font-size: 13px;
}
.empty-state .btn-sm { margin-top: 12px; display: inline-block; }
</style>
