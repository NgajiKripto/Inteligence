<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">◈</span>
        <span class="logo-text">MEMECOIN<br><span class="logo-sub">INTELLIGENCE</span></span>
      </div>
    </div>

    <nav class="nav-menu">
      <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
        <span class="nav-icon">⬡</span>
        <span>Dashboard</span>
      </router-link>
      <router-link to="/trending" class="nav-item" :class="{ active: $route.path === '/trending' }">
        <span class="nav-icon">↗</span>
        <span>Trending</span>
      </router-link>
      <router-link to="/analyze" class="nav-item" :class="{ active: $route.path === '/analyze' }">
        <span class="nav-icon">◎</span>
        <span>Analyze Token</span>
      </router-link>
      <router-link to="/signals" class="nav-item" :class="{ active: $route.path === '/signals' }">
        <span class="nav-icon">⚡</span>
        <span>Signals</span>
      </router-link>
      <router-link to="/chat" class="nav-item" :class="{ active: $route.path === '/chat' }">
        <span class="nav-icon">◉</span>
        <span>AI Analyst</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-text">System Active</span>
      </div>
      <div class="version">v1.0.0</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: 240px;
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid var(--border);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 28px;
  color: var(--accent-green);
}

.logo-text {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  line-height: 1.4;
  color: var(--text-primary);
}

.logo-sub {
  color: var(--accent-green);
  font-size: 10px;
}

.nav-menu {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  text-decoration: none;
}

.nav-item.active {
  background: rgba(0, 255, 136, 0.08);
  color: var(--accent-green);
  border: 1px solid rgba(0, 255, 136, 0.15);
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-green);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.status-text {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.version {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
</style>
