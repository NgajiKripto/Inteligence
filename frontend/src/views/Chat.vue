<template>
  <div class="chat-page">
    <header class="page-header">
      <h1>AI Analyst</h1>
      <p class="subtitle">Ask anything about memecoins — risk, sentiment, whale activity, strategy</p>
    </header>

    <div class="chat-container">
      <!-- Messages -->
      <div class="messages" ref="messagesContainer">
        <div v-if="!messages.length" class="welcome-msg">
          <div class="welcome-icon">◉</div>
          <h2>MemeCoin Intelligence Analyst</h2>
          <p>I can help you analyze tokens, assess risk, check whale activity, and discuss trading strategies.</p>
          <div class="suggestions">
            <button @click="sendSuggestion(s)" v-for="s in suggestions" :key="s" class="suggestion-btn">
              {{ s }}
            </button>
          </div>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
          <div class="msg-avatar">{{ msg.role === 'user' ? '◇' : '◈' }}</div>
          <div class="msg-content">
            <div class="msg-text" v-html="formatMessage(msg.content)"></div>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="msg-avatar">◈</div>
          <div class="msg-content">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="chat-input-bar">
        <input
          v-model="userInput"
          @keydown.enter="sendMessage"
          placeholder="Ask about a token, market sentiment, or trading strategy..."
          :disabled="loading"
          class="chat-input"
        />
        <button @click="sendMessage" :disabled="!userInput.trim() || loading" class="send-btn">
          →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { analysisApi } from '../api'

const messages = ref([])
const userInput = ref('')
const loading = ref(false)
const messagesContainer = ref(null)

const suggestions = [
  "What are the riskiest memecoins right now?",
  "How do I spot a rug pull?",
  "Explain smart money tracking for Solana",
  "What should I look for before buying a memecoin?"
]

const sendSuggestion = (text) => {
  userInput.value = text
  sendMessage()
}

const sendMessage = async () => {
  const text = userInput.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  userInput.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const resp = await analysisApi.chat({
      message: text,
      chat_history: messages.value.slice(-10)
    })

    const response = resp.data?.data?.response || 'Sorry, I could not process that request.'
    messages.value.push({ role: 'assistant', content: response })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: `Error: ${e.response?.data?.error || e.message}. Please check your API configuration.`
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const formatMessage = (text) => {
  // Basic markdown-like formatting
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.chat-page {
  max-width: 900px;
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.page-header { margin-bottom: 16px; flex-shrink: 0; }
.page-header h1 { font-size: 28px; font-weight: 600; }
.subtitle { color: var(--text-secondary); font-size: 14px; margin-top: 4px; }

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.welcome-msg {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-secondary);
}
.welcome-icon { font-size: 48px; color: var(--accent-green); margin-bottom: 16px; }
.welcome-msg h2 { font-size: 20px; color: var(--text-primary); margin-bottom: 8px; }
.welcome-msg p { font-size: 14px; margin-bottom: 24px; }

.suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.suggestion-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 8px 16px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.suggestion-btn:hover { border-color: var(--accent-green); color: var(--accent-green); }

.message {
  display: flex;
  gap: 12px;
  max-width: 85%;
}
.message.user { align-self: flex-end; flex-direction: row-reverse; }
.message.assistant { align-self: flex-start; }

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.message.user .msg-avatar { background: var(--bg-hover); color: var(--text-primary); }
.message.assistant .msg-avatar { background: rgba(0,255,136,0.1); color: var(--accent-green); }

.msg-content {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
}
.message.user .msg-content { background: rgba(0,255,136,0.08); border: 1px solid rgba(0,255,136,0.15); }

.msg-text code {
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.typing-indicator span {
  width: 8px; height: 8px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.chat-input-bar {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
}

.chat-input {
  flex: 1;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--text-primary);
  font-size: 14px;
}
.chat-input:focus { border-color: var(--accent-green); outline: none; }

.send-btn {
  width: 44px;
  height: 44px;
  background: var(--accent-green);
  border: none;
  border-radius: 8px;
  color: #000;
  font-size: 20px;
  font-weight: 700;
  cursor: pointer;
}
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
