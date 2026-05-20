<template>
  <div class="trending-page">
    <header class="page-header">
      <h1>Trending Memecoins</h1>
      <p class="subtitle">Top tokens by volume, social buzz, and price action</p>
    </header>

    <!-- Filters -->
    <div class="filter-bar">
      <select v-model="chain" @change="fetchTrending" class="filter-select">
        <option value="all">All Chains</option>
        <option value="solana">Solana</option>
        <option value="ethereum">Ethereum</option>
        <option value="bsc">BSC</option>
      </select>
      <select v-model="sortBy" @change="fetchTrending" class="filter-select">
        <option value="volume">By Volume</option>
        <option value="gainers">Top Gainers</option>
        <option value="social">Social Buzz</option>
      </select>
      <select v-model="timeframe" @change="fetchTrending" class="filter-select">
        <option value="1h">1 Hour</option>
        <option value="6h">6 Hours</option>
        <option value="24h">24 Hours</option>
      </select>
      <button @click="fetchTrending" class="refresh-btn">↻ Refresh</button>
    </div>

    <!-- Token Table -->
    <div class="table-container">
      <div class="table-header">
        <span class="col-rank">#</span>
        <span class="col-token">Token</span>
        <span class="col-price">Price</span>
        <span class="col-change">24h</span>
        <span class="col-volume">Volume 24h</span>
        <span class="col-liq">Liquidity</span>
        <span class="col-action">Action</span>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>Fetching trending tokens...</span>
      </div>

      <div v-else-if="tokens.length" class="table-body">
        <div class="table-row" v-for="(token, idx) in tokens" :key="idx">
          <span class="col-rank">{{ idx + 1 }}</span>
          <span class="col-token">
            <span class="token-symbol">{{ token.symbol }}</span>
            <span class="token-name">{{ token.name }}</span>
          </span>
          <span class="col-price mono">${{ formatPrice(token.metrics?.price_usd) }}</span>
          <span class="col-change mono" :class="token.metrics?.price_change_24h >= 0 ? 'positive' : 'negative'">
            {{ formatChange(token.metrics?.price_change_24h) }}%
          </span>
          <span class="col-volume mono">${{ formatLarge(token.metrics?.volume_24h) }}</span>
          <span class="col-liq mono">${{ formatLarge(token.metrics?.liquidity_usd) }}</span>
          <span class="col-action">
            <button @click="analyzeToken(token)" class="analyze-btn">Analyze</button>
          </span>
        </div>
      </div>

      <div v-else class="empty-state">
        <p>No trending tokens found. Try different filters or check your API connection.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { tokenApi } from '../api'

const router = useRouter()
const tokens = ref([])
const loading = ref(false)
const chain = ref('all')
const sortBy = ref('volume')
const timeframe = ref('24h')

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

const formatLarge = (num) => {
  if (!num) return '0'
  if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
  return num.toFixed(0)
}

const fetchTrending = async () => {
  loading.value = true
  try {
    const resp = await tokenApi.trending({
      chain: chain.value,
      timeframe: timeframe.value,
      sort_by: sortBy.value,
      limit: 30
    })
    tokens.value = resp.data?.data?.tokens || []
  } catch (e) {
    console.error('Fetch trending failed:', e)
  } finally {
    loading.value = false
  }
}

const analyzeToken = (token) => {
  router.push({ path: '/analyze', query: { address: token.contract_address, chain: token.chain } })
}

onMounted(fetchTrending)
</script>

<style scoped>
.trending-page { max-width: 1200px; }

.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 28px; font-weight: 600; }
.subtitle { color: var(--text-secondary); font-size: 14px; margin-top: 4px; }

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-select {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 16px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
}
.filter-select:focus { border-color: var(--accent-green); outline: none; }

.refresh-btn {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 16px;
  color: var(--accent-green);
  font-size: 13px;
  cursor: pointer;
}
.refresh-btn:hover { background: var(--bg-hover); }

.table-container {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.table-header, .table-row {
  display: grid;
  grid-template-columns: 50px 2fr 1fr 0.8fr 1fr 1fr 0.8fr;
  align-items: center;
  padding: 12px 20px;
}

.table-header {
  background: var(--bg-secondary);
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 1px solid var(--border);
}

.table-row {
  font-size: 13px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  transition: background 0.2s;
}
.table-row:hover { background: var(--bg-hover); }

.col-rank { color: var(--text-muted); font-family: var(--font-mono); }
.token-symbol { font-family: var(--font-mono); font-weight: 600; }
.token-name { color: var(--text-muted); font-size: 11px; margin-left: 8px; }
.mono { font-family: var(--font-mono); }
.positive { color: var(--accent-green); }
.negative { color: var(--accent-red); }

.analyze-btn {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.2);
  border-radius: 6px;
  padding: 6px 12px;
  color: var(--accent-green);
  font-size: 11px;
  cursor: pointer;
  font-family: var(--font-mono);
}
.analyze-btn:hover { background: rgba(0, 255, 136, 0.2); }

.loading-state {
  padding: 48px;
  text-align: center;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--accent-green);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { padding: 48px; text-align: center; color: var(--text-muted); font-size: 13px; }
</style>
