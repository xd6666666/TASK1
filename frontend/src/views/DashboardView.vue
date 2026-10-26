<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchDashboard } from '@/api/dashboard'

const router = useRouter()
const loading = ref(false)
const data = ref<any>(null)

const kpis = computed(() => data.value?.kpi || {})
const trend = computed(() => data.value?.trend || [])
const channels = computed(() => data.value?.channels || [])
const hitTop = computed(() => data.value?.hit_top || [])
const qaBars = computed(() => data.value?.qa_bars || [])
const alerts = computed(() => data.value?.alerts || [])

const maxHit = computed(() => Math.max(...hitTop.value.map((x: any) => x.hits || 0), 1))
const maxChannel = computed(() => Math.max(...channels.value.map((x: any) => x.count || 0), 1))
const maxTrend = computed(() => Math.max(...trend.value.map((x: any) => x.total || 0), 1))

async function load() {
  loading.value = true
  try {
    const res: any = await fetchDashboard()
    data.value = res.data
  } finally {
    loading.value = false
  }
}

function goto(page: string) {
  if (page) router.push('/' + page)
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-card head">
      <div>
        <h2>运营概览</h2>
        <p class="muted">智能客服全链路运营数据 · 会话 / AI / 知识 / 质检</p>
      </div>
      <el-button type="primary" @click="router.push('/workspace')">进入工作台</el-button>
    </div>

    <div class="kpi-grid">
      <div class="page-card kpi">
        <div class="label">会话量</div>
        <div class="value">{{ kpis.sessions_today || 0 }}</div>
        <div class="foot">进行中 {{ kpis.active || 0 }}</div>
      </div>
      <div class="page-card kpi">
        <div class="label">AI 辅助占比</div>
        <div class="value">{{ kpis.ai_resolve_rate || 0 }}<small>%</small></div>
        <div class="foot">目标 75%</div>
      </div>
      <div class="page-card kpi">
        <div class="label">平均首响</div>
        <div class="value">{{ kpis.avg_first_response_sec || 0 }}<small>秒</small></div>
        <div class="foot">较上周更快</div>
      </div>
      <div class="page-card kpi">
        <div class="label">质检合格率</div>
        <div class="value">{{ kpis.qa_pass_rate || 0 }}<small>%</small></div>
        <div class="foot">待复核 {{ kpis.pending_review || 0 }}</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="page-card">
        <h3>会话趋势（近 7 天）</h3>
        <div class="bars">
          <div v-for="d in trend" :key="d.date" class="bar-col">
            <div class="stack">
              <i class="ai" :style="{ height: (d.ai / maxTrend) * 120 + 'px' }" />
              <i class="human" :style="{ height: (d.human / maxTrend) * 120 + 'px' }" />
            </div>
            <span>{{ d.date.slice(5) }}</span>
          </div>
        </div>
        <div class="legend muted">
          <span class="dot ai" /> AI 解决
          <span class="dot human" /> 转人工
        </div>
      </div>
      <div class="page-card">
        <h3>渠道分布</h3>
        <div v-for="c in channels" :key="c.channel" class="hbar">
          <div class="top"><span>{{ c.label }}</span><b>{{ c.count }}</b></div>
          <div class="track"><i :style="{ width: (c.count / maxChannel) * 100 + '%' }" /></div>
        </div>
        <el-empty v-if="!channels.length" description="暂无渠道数据" :image-size="48" />
      </div>
    </div>

    <div class="grid-3">
      <div class="page-card">
        <h3>知识命中 Top</h3>
        <div v-for="h in hitTop" :key="h.title" class="hbar">
          <div class="top"><span>{{ h.title }}</span><b>{{ h.hits }}</b></div>
          <div class="track"><i class="teal" :style="{ width: (h.hits / maxHit) * 100 + '%' }" /></div>
        </div>
      </div>
      <div class="page-card">
        <h3>质检分布</h3>
        <div v-for="q in qaBars" :key="q.name" class="hbar">
          <div class="top"><span>{{ q.name }}</span><b>{{ q.value }}</b></div>
          <div class="track"><i class="warn" :style="{ width: Math.min(100, q.value * 10) + '%' }" /></div>
        </div>
      </div>
      <div class="page-card">
        <h3>实时预警</h3>
        <div v-for="a in alerts" :key="a.id" class="alert">
          <el-tag size="small" :type="a.level === 'danger' ? 'danger' : a.level === 'ok' ? 'success' : 'warning'">
            {{ a.level }}
          </el-tag>
          <div class="txt">
            <p>{{ a.title }}</p>
            <small class="muted">{{ a.detail }}</small>
          </div>
          <el-button v-if="a.link_page" size="small" @click="goto(a.link_page)">查看</el-button>
        </div>
        <el-empty v-if="!alerts.length" description="暂无预警" :image-size="48" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.head h2 { margin: 0 0 4px; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
.kpi .label { color: var(--zf-muted); font-size: 13px; }
.kpi .value { font-size: 28px; font-weight: 700; margin: 8px 0 4px; }
.kpi .value small { font-size: 14px; margin-left: 2px; }
.kpi .foot { font-size: 12px; color: var(--zf-muted); }
.grid-2 { display: grid; grid-template-columns: 1.4fr 1fr; gap: 12px; margin-bottom: 12px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: 12px; }
h3 { margin: 0 0 12px; font-size: 14px; }
.bars { display: flex; align-items: flex-end; gap: 10px; height: 150px; padding-top: 8px; }
.bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 11px; color: var(--zf-muted); }
.stack { display: flex; flex-direction: column-reverse; width: 70%; gap: 2px; }
.stack i { display: block; border-radius: 4px 4px 0 0; }
.stack .ai { background: #4f46e5; }
.stack .human { background: #f0b46a; }
.legend { display: flex; gap: 12px; margin-top: 10px; font-size: 12px; align-items: center; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px; }
.dot.ai { background: #4f46e5; }
.dot.human { background: #f0b46a; }
.hbar { margin-bottom: 10px; }
.hbar .top { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; gap: 8px; }
.hbar .top span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.track { height: 8px; background: #eef1f7; border-radius: 99px; overflow: hidden; }
.track i { display: block; height: 100%; background: #4f46e5; border-radius: 99px; }
.track i.teal { background: #0d9494; }
.track i.warn { background: #d97706; }
.alert { display: flex; gap: 8px; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid var(--zf-line); }
.alert .txt { flex: 1; min-width: 0; }
.alert p { margin: 0 0 2px; font-size: 13px; line-height: 1.4; }
@media (max-width: 1100px) {
  .kpi-grid, .grid-2, .grid-3 { grid-template-columns: 1fr; }
}
</style>
