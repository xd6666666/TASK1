<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  aiSuggest,
  closeConversation,
  getConversation,
  listConversations,
  sendMessage,
} from '@/api/workspace'

type Conv = {
  id: number
  session_no: string
  channel: string
  channel_label: string
  status: string
  subject: string
  customer_name: string
  customer_level: string
  customer_phone: string
  customer_tags: string
  last_message: string
}

type Msg = {
  id: number
  sender: string
  content: string
  is_ai_assisted: boolean
  created_at?: string
}

const loading = ref(false)
const list = ref<Conv[]>([])
const activeId = ref<number | null>(null)
const messages = ref<Msg[]>([])
const active = ref<Conv | null>(null)
const statusFilter = ref('all')
const channelFilter = ref('all')
const keyword = ref('')
const draft = ref('')
const aiLoading = ref(false)
const aiBox = ref<{ reply: string; confidence: number; citations: any[]; mock: boolean } | null>(null)
const chatBody = ref<HTMLElement | null>(null)

const channelOptions = [
  { value: 'all', label: '全部渠道' },
  { value: 'wechat_mp', label: '微信公众号' },
  { value: 'wecom', label: '企业微信' },
  { value: 'app', label: 'App' },
  { value: 'web', label: 'Web 官网' },
]

const filteredHint = computed(() => {
  const n = list.value.length
  const activeN = list.value.filter((c) => c.status === 'active').length
  const queueN = list.value.filter((c) => c.status === 'queue').length
  return `全部 ${n} · 进行中 ${activeN} · 排队 ${queueN}`
})

async function loadList() {
  loading.value = true
  try {
    const res: any = await listConversations({
      status: statusFilter.value,
      channel: channelFilter.value,
      q: keyword.value,
    })
    list.value = res.data || []
    if (!activeId.value && list.value.length) {
      await openConv(list.value[0].id)
    } else if (activeId.value) {
      const still = list.value.find((c) => c.id === activeId.value)
      if (!still && list.value.length) await openConv(list.value[0].id)
    }
  } finally {
    loading.value = false
  }
}

async function openConv(id: number) {
  activeId.value = id
  aiBox.value = null
  const res: any = await getConversation(id)
  active.value = res.data.conversation
  messages.value = res.data.messages || []
  await nextTick()
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  await loadAi()
}

async function loadAi() {
  if (!activeId.value) return
  aiLoading.value = true
  try {
    const res: any = await aiSuggest(activeId.value)
    aiBox.value = res.data
  } catch {
    aiBox.value = null
  } finally {
    aiLoading.value = false
  }
}

function useAi() {
  if (!aiBox.value) return
  draft.value = aiBox.value.reply
}

async function send(fromAi = false) {
  if (!activeId.value || !draft.value.trim()) return
  const content = draft.value.trim()
  const res: any = await sendMessage(activeId.value, content, fromAi)
  messages.value.push(res.data)
  draft.value = ''
  ElMessage.success('已发送')
  await loadList()
  await nextTick()
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
}

async function sendAiDirect() {
  if (!aiBox.value) return
  draft.value = aiBox.value.reply
  await send(true)
  aiBox.value = null
}

async function endChat() {
  if (!activeId.value) return
  await closeConversation(activeId.value)
  ElMessage.success('会话已结束')
  await loadList()
  if (activeId.value) await openConv(activeId.value)
}

watch([statusFilter, channelFilter], () => loadList())

onMounted(loadList)
</script>

<template>
  <div class="ws" v-loading="loading">
    <aside class="list">
      <div class="filters">
        <el-segmented
          v-model="statusFilter"
          :options="[
            { label: '全部', value: 'all' },
            { label: '进行中', value: 'active' },
            { label: '排队', value: 'queue' },
            { label: '已结束', value: 'closed' },
          ]"
          size="small"
        />
        <el-select v-model="channelFilter" size="small" style="width: 100%; margin-top: 8px">
          <el-option v-for="c in channelOptions" :key="c.value" :label="c.label" :value="c.value" />
        </el-select>
        <el-input
          v-model="keyword"
          size="small"
          clearable
          placeholder="搜索客户 / 会话"
          style="margin-top: 8px"
          @keyup.enter="loadList"
          @clear="loadList"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <div class="hint">{{ filteredHint }}</div>
      </div>
      <div class="conv-list">
        <button
          v-for="c in list"
          :key="c.id"
          class="conv"
          :class="{ active: c.id === activeId }"
          @click="openConv(c.id)"
        >
          <div class="row">
            <strong>{{ c.customer_name }}</strong>
            <el-tag size="small" effect="plain">{{ c.channel_label }}</el-tag>
          </div>
          <div class="sub">{{ c.session_no }} · {{ c.subject || '会话' }}</div>
          <div class="preview">{{ c.last_message }}</div>
          <el-tag
            size="small"
            :type="c.status === 'active' ? 'success' : c.status === 'queue' ? 'warning' : 'info'"
          >
            {{ c.status === 'active' ? '进行中' : c.status === 'queue' ? '排队' : '已结束' }}
          </el-tag>
        </button>
        <el-empty v-if="!list.length" description="暂无会话" :image-size="64" />
      </div>
    </aside>

    <section class="chat" v-if="active">
      <header class="chat-head">
        <div>
          <div class="name">
            {{ active.customer_name }}
            <el-tag size="small" type="primary">{{ active.customer_level }}</el-tag>
          </div>
          <div class="meta">
            {{ active.channel_label }} · {{ active.session_no }} · {{ active.customer_phone }}
          </div>
        </div>
        <el-button type="danger" plain size="small" :disabled="active.status === 'closed'" @click="endChat">
          结束会话
        </el-button>
      </header>

      <div ref="chatBody" class="chat-body">
        <div
          v-for="m in messages"
          :key="m.id"
          class="bubble"
          :class="m.sender"
        >
          <div class="who">
            {{ m.sender === 'customer' ? '客户' : m.sender === 'agent' ? '坐席' : '系统' }}
            <el-tag v-if="m.is_ai_assisted" size="small" type="success" effect="plain">AI 辅助</el-tag>
          </div>
          <div class="text">{{ m.content }}</div>
        </div>
      </div>

      <div class="ai" v-loading="aiLoading">
        <div class="ai-head">
          <span><el-icon><MagicStick /></el-icon> AI 推荐回复</span>
          <span class="conf" v-if="aiBox">
            置信度 {{ Math.round((aiBox.confidence || 0) * 100) }}%
            · 引用 {{ aiBox.citations?.length || 0 }} 条
            <el-tag v-if="aiBox.mock" size="small" type="warning">Mock</el-tag>
          </span>
          <el-button link type="primary" :loading="aiLoading" @click="loadAi">换一个</el-button>
        </div>
        <p v-if="aiBox">{{ aiBox.reply }}</p>
        <p v-else class="muted">等待生成推荐答案…</p>
        <div class="ai-acts" v-if="aiBox">
          <el-button type="primary" size="small" @click="useAi">采纳并编辑</el-button>
          <el-button size="small" @click="sendAiDirect">确认发送</el-button>
          <div class="cites" v-if="aiBox.citations?.length">
            <el-tag
              v-for="(c, i) in aiBox.citations"
              :key="i"
              size="small"
              effect="plain"
              style="margin: 2px"
            >
              {{ c.title }} ({{ c.score }})
            </el-tag>
          </div>
        </div>
      </div>

      <div class="composer">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          :disabled="active.status === 'closed'"
          placeholder="确认或编辑回复后发送。Enter 发送可用 Ctrl+Enter"
          @keydown.ctrl.enter.exact="send(false)"
        />
        <div class="composer-foot">
          <span class="muted">人工确认后再发送 · 支持 AI 推荐草稿</span>
          <el-button type="primary" :disabled="!draft.trim() || active.status === 'closed'" @click="send(false)">
            发送
          </el-button>
        </div>
      </div>
    </section>

    <aside class="side" v-if="active">
      <div class="block">
        <h3>客户资料</h3>
        <dl>
          <div><dt>姓名</dt><dd>{{ active.customer_name }}</dd></div>
          <div><dt>手机</dt><dd>{{ active.customer_phone }}</dd></div>
          <div><dt>等级</dt><dd>{{ active.customer_level }}</dd></div>
          <div><dt>标签</dt><dd>{{ active.customer_tags || '-' }}</dd></div>
          <div><dt>渠道</dt><dd>{{ active.channel_label }}</dd></div>
        </dl>
      </div>
      <div class="block">
        <h3>渠道说明</h3>
        <p class="muted">
          当前演示数据覆盖微信公众号、企业微信、App、Web 官网四类接入。真实渠道 webhook 可后续对接，会话模型已按渠道字段预留。
        </p>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.ws {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 260px;
  gap: 12px;
  min-height: calc(100vh - 120px);
}
.list, .chat, .side {
  background: #fff;
  border: 1px solid var(--zf-line);
  border-radius: 14px;
  min-height: 0;
}
.list { display: flex; flex-direction: column; overflow: hidden; }
.filters { padding: 12px; border-bottom: 1px solid var(--zf-line); }
.hint { margin-top: 8px; font-size: 12px; color: var(--zf-muted); }
.conv-list { overflow: auto; padding: 8px; flex: 1; }
.conv {
  width: 100%; text-align: left; border: 0; background: transparent;
  border-radius: 10px; padding: 10px; cursor: pointer; margin-bottom: 4px;
}
.conv.active, .conv:hover { background: var(--zf-primary-soft); }
.conv .row { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.conv .sub { font-size: 12px; color: var(--zf-muted); margin: 4px 0; }
.conv .preview {
  font-size: 12px; color: #445; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 6px;
}
.chat { display: flex; flex-direction: column; overflow: hidden; }
.chat-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid var(--zf-line);
}
.name { font-weight: 650; display: flex; gap: 8px; align-items: center; }
.meta { font-size: 12px; color: var(--zf-muted); margin-top: 4px; }
.chat-body { flex: 1; overflow: auto; padding: 16px; background: linear-gradient(180deg, #f7f8fc, #fff); }
.bubble { max-width: 78%; margin-bottom: 12px; }
.bubble.customer { margin-right: auto; }
.bubble.agent { margin-left: auto; }
.bubble.system { margin: 8px auto; max-width: 90%; text-align: center; }
.bubble .who { font-size: 11px; color: var(--zf-muted); margin-bottom: 4px; display: flex; gap: 6px; align-items: center; }
.bubble.agent .who { justify-content: flex-end; }
.bubble .text {
  padding: 10px 12px; border-radius: 12px; background: #fff;
  border: 1px solid var(--zf-line); white-space: pre-wrap; line-height: 1.55; font-size: 14px;
}
.bubble.agent .text { background: #eef0ff; border-color: #d8dcff; }
.bubble.system .text { background: transparent; border: 0; color: var(--zf-muted); font-size: 12px; }
.ai {
  margin: 0 12px; padding: 12px; border: 1px dashed #b7c0ff; border-radius: 12px;
  background: #f7f8ff;
}
.ai-head { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 13px; }
.conf { margin-left: auto; font-weight: 400; color: var(--zf-muted); font-size: 12px; }
.ai p { margin: 8px 0; white-space: pre-wrap; line-height: 1.55; font-size: 13px; }
.ai-acts { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.cites { width: 100%; margin-top: 4px; }
.composer { padding: 12px; border-top: 1px solid var(--zf-line); }
.composer-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.side { padding: 14px; overflow: auto; }
.block { margin-bottom: 18px; }
.block h3 { margin: 0 0 10px; font-size: 14px; }
.block dl { margin: 0; }
.block dl > div {
  display: flex; justify-content: space-between; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid var(--zf-line); font-size: 13px;
}
.block dt { color: var(--zf-muted); }
.block dd { margin: 0; text-align: right; }
@media (max-width: 1100px) {
  .ws { grid-template-columns: 240px minmax(0, 1fr); }
  .side { display: none; }
}
</style>
