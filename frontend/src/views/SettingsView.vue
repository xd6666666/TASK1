<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchSettings, modelHealth, saveSettings } from '@/api/settings'

const loading = ref(false)
const health = ref<any>(null)
const form = reactive<any>({
  ai: { profile: 'pro', temperature: 0.4, show_citations: true, llm_mock: true, llm_model: '', llm_base_url: '' },
  channels: [],
  qa_notify: {
    auto_inspect: true,
    high_risk_alert: true,
    daily_report: true,
    sample_ratio: 25,
    low_score_review: true,
  },
  team: { agents: 12, online: 8, busy: 2, qa_staff: 3, kb_ops: 2, retention_days: 180 },
})

async function load() {
  loading.value = true
  try {
    const res: any = await fetchSettings()
    Object.assign(form.ai, res.data.ai || {})
    form.channels = res.data.channels || []
    Object.assign(form.qa_notify, res.data.qa_notify || {})
    Object.assign(form.team, res.data.team || {})
    const h: any = await modelHealth()
    health.value = h.data
  } finally {
    loading.value = false
  }
}

async function save() {
  await saveSettings({
    ai: form.ai,
    channels: form.channels,
    qa_notify: form.qa_notify,
    team: form.team,
  })
  ElMessage.success('设置已保存')
  await load()
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-card head">
      <div>
        <h2>系统设置</h2>
        <p class="muted">配置 AI 模型、服务渠道与团队协作方式。</p>
      </div>
      <el-button type="primary" @click="save">保存更改</el-button>
    </div>

    <div class="grid">
      <div class="page-card">
        <div class="ch">
          <h3>AI 模型配置</h3>
          <el-tag :type="health?.ok ? 'success' : 'warning'" size="small">
            {{ health?.mode === 'mock' ? 'Mock 模式' : health?.ok ? '节点正常' : '节点异常' }}
          </el-tag>
        </div>
        <el-radio-group v-model="form.ai.profile" class="profiles">
          <el-radio value="pro" border>智服大模型 Pro</el-radio>
          <el-radio value="flash" border>智服大模型 Flash</el-radio>
          <el-radio value="private" border>私有化模型节点</el-radio>
        </el-radio-group>
        <div class="row"><span>模型</span><code>{{ form.ai.llm_model || '-' }}</code></div>
        <div class="row"><span>Base URL</span><code class="url">{{ form.ai.llm_base_url || '-' }}</code></div>
        <div class="row">
          <span>答案温度</span>
          <el-slider v-model="form.ai.temperature" :min="0" :max="1" :step="0.1" style="width:180px" />
          <b>{{ form.ai.temperature }}</b>
        </div>
        <div class="row">
          <span>答案附带引用来源</span>
          <el-switch v-model="form.ai.show_citations" />
        </div>
        <p class="muted tip">切换真实 Qwen：在 backend/.env 设置 LLM_MOCK=false 并配置本地推理地址后重启后端。</p>
      </div>

      <div class="page-card">
        <h3>服务渠道</h3>
        <div v-for="c in form.channels" :key="c.key" class="row">
          <div>
            <div>{{ c.name }}</div>
            <small class="muted">{{ c.key }} · {{ c.status }}</small>
          </div>
          <el-switch v-model="c.enabled" />
        </div>
        <p class="muted tip">当前为配置面模拟；真实公众号/企微 webhook 可在此开关就绪后接入。</p>
      </div>

      <div class="page-card">
        <h3>质检与通知</h3>
        <div class="row"><span>全量自动质检</span><el-switch v-model="form.qa_notify.auto_inspect" /></div>
        <div class="row"><span>高风险实时告警</span><el-switch v-model="form.qa_notify.high_risk_alert" /></div>
        <div class="row"><span>每日质检日报</span><el-switch v-model="form.qa_notify.daily_report" /></div>
        <div class="row"><span>低分自动复核</span><el-switch v-model="form.qa_notify.low_score_review" /></div>
        <div class="row">
          <span>抽检比例</span>
          <el-select v-model="form.qa_notify.sample_ratio" style="width:120px">
            <el-option :value="25" label="25%" />
            <el-option :value="50" label="50%" />
            <el-option :value="100" label="100%" />
          </el-select>
        </div>
      </div>

      <div class="page-card">
        <h3>团队与权限</h3>
        <div class="row"><span>客服坐席</span><b>{{ form.team.online }} / {{ form.team.agents }} 在线</b></div>
        <div class="row"><span>质检员</span><b>{{ form.team.qa_staff }} 人</b></div>
        <div class="row"><span>知识运营</span><b>{{ form.team.kb_ops }} 人</b></div>
        <div class="row">
          <span>会话保留天数</span>
          <el-select v-model="form.team.retention_days" style="width:140px">
            <el-option :value="180" label="180 天" />
            <el-option :value="365" label="365 天" />
            <el-option :value="0" label="永久" />
          </el-select>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
.head h2 { margin:0 0 4px; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
h3 { margin:0; font-size:14px; }
.ch { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
.profiles { display:flex; flex-direction:column; gap:8px; width:100%; margin-bottom:12px; }
.row { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:10px 0; border-bottom:1px solid var(--zf-line); font-size:13px; }
code { font-size:12px; background:#f3f5fb; padding:2px 6px; border-radius:6px; }
code.url { max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; display:inline-block; }
.tip { margin:12px 0 0; font-size:12px; line-height:1.5; }
@media (max-width:960px){ .grid { grid-template-columns:1fr; } }
</style>
