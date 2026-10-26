<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createRule,
  deleteRule,
  fetchQaOverview,
  listReviews,
  listRules,
  reviewResult,
  runInspect,
  updateRule,
} from '@/api/qa'

const tab = ref('overview')
const loading = ref(false)
const overview = ref<any>(null)
const rules = ref<any[]>([])
const reviews = ref<any[]>([])
const ruleDialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  group_name: '服务规范',
  description: '',
  severity: 'medium',
  enabled: true,
  check_prompt: '',
})

async function loadOverview() {
  const res: any = await fetchQaOverview()
  overview.value = res.data
}

async function loadRules() {
  const res: any = await listRules()
  rules.value = res.data || []
}

async function loadReviews() {
  const res: any = await listReviews()
  reviews.value = res.data || []
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadOverview(), loadRules(), loadReviews()])
  } finally {
    loading.value = false
  }
}

async function inspect() {
  loading.value = true
  try {
    const res: any = await runInspect()
    ElMessage.success(`已完成抽检 ${res.data.count} 通`)
    await loadAll()
    tab.value = 'overview'
  } finally {
    loading.value = false
  }
}

function openRule(row?: any) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, row)
  } else {
    editingId.value = null
    Object.assign(form, {
      name: '',
      group_name: '服务规范',
      description: '',
      severity: 'medium',
      enabled: true,
      check_prompt: '',
    })
  }
  ruleDialog.value = true
}

async function saveRule() {
  const payload = { ...form }
  if (editingId.value) await updateRule(editingId.value, payload)
  else await createRule(payload)
  ElMessage.success('规则已保存')
  ruleDialog.value = false
  await loadRules()
}

async function removeRule(row: any) {
  await ElMessageBox.confirm(`删除规则「${row.name}」？`, '确认', { type: 'warning' })
  await deleteRule(row.id)
  await loadRules()
}

async function doReview(row: any, pass: boolean) {
  await reviewResult(row.id, pass, pass ? '人工复核通过' : '人工复核不通过')
  ElMessage.success('已处理')
  await loadAll()
}

onMounted(loadAll)
</script>

<template>
  <div v-loading="loading">
    <div class="page-card head">
      <div>
        <h2>质检系统</h2>
        <p class="muted">全量 AI 自动质检 + 规则引擎，覆盖服务规范、合规与解决质量。</p>
      </div>
      <el-button type="primary" @click="inspect">发起抽检</el-button>
    </div>

    <div class="kpi-grid" v-if="overview">
      <div class="page-card kpi"><div class="l">抽检覆盖率</div><div class="v">{{ overview.kpi.coverage }}%</div><div class="f">{{ overview.kpi.sampled }} / {{ overview.kpi.total_sessions }}</div></div>
      <div class="page-card kpi"><div class="l">平均得分</div><div class="v">{{ overview.kpi.avg_score }}</div><div class="f">分</div></div>
      <div class="page-card kpi"><div class="l">风险会话</div><div class="v">{{ overview.kpi.risk_count }}</div><div class="f">需关注</div></div>
      <div class="page-card kpi"><div class="l">待复核</div><div class="v">{{ overview.kpi.pending_review }}</div><div class="f">人工队列</div></div>
    </div>

    <div class="page-card" style="margin-top:12px">
      <el-tabs v-model="tab">
        <el-tab-pane label="质检概览" name="overview">
          <el-table :data="overview?.results || []" stripe>
            <el-table-column prop="session_no" label="会话" width="120" />
            <el-table-column prop="customer_name" label="客户" width="100" />
            <el-table-column prop="score" label="得分" width="80" />
            <el-table-column label="命中规则" min-width="180">
              <template #default="{ row }">
                <el-tag v-for="(h, i) in row.hit_rules || []" :key="i" size="small" style="margin:2px">{{ h }}</el-tag>
                <span v-if="!(row.hit_rules || []).length" class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="level" label="等级" width="90" />
            <el-table-column prop="status" label="状态" width="120" />
            <el-table-column prop="summary" label="摘要" min-width="180" show-overflow-tooltip />
          </el-table>
          <div class="radar" v-if="overview?.radar">
            <h4>能力雷达（团队均值）</h4>
            <div v-for="(v, k) in overview.radar" :key="k" class="hbar">
              <div class="top"><span>{{ k }}</span><b>{{ v }}</b></div>
              <div class="track"><i :style="{ width: v + '%' }" /></div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="`规则配置 (${rules.length})`" name="rules">
          <div style="margin-bottom:10px">
            <el-button type="primary" size="small" @click="openRule()">新增规则</el-button>
          </div>
          <el-table :data="rules" stripe>
            <el-table-column prop="name" label="规则" />
            <el-table-column prop="group_name" label="分组" width="120" />
            <el-table-column prop="severity" label="级别" width="100" />
            <el-table-column label="启用" width="80">
              <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column prop="description" label="说明" show-overflow-tooltip />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button link type="primary" @click="openRule(row)">编辑</el-button>
                <el-button link type="danger" @click="removeRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`复核队列 (${reviews.length})`" name="review">
          <div v-for="r in reviews" :key="r.id" class="review">
            <div>
              <strong>{{ r.session_no }} · {{ r.customer_name }}</strong>
              <div class="muted">得分 {{ r.score }} · {{ r.summary }}</div>
            </div>
            <div>
              <el-button size="small" type="success" @click="doReview(r, true)">通过</el-button>
              <el-button size="small" type="danger" @click="doReview(r, false)">驳回</el-button>
            </div>
          </div>
          <el-empty v-if="!reviews.length" description="暂无待复核" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="ruleDialog" :title="editingId ? '编辑规则' : '新增规则'" width="560px">
      <el-form label-position="top">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="分组">
          <el-select v-model="form.group_name" style="width:100%">
            <el-option label="服务规范" value="服务规范" />
            <el-option label="合规风控" value="合规风控" />
            <el-option label="解决质量" value="解决质量" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-radio-group v-model="form.severity">
            <el-radio value="low">低</el-radio>
            <el-radio value="medium">中</el-radio>
            <el-radio value="high">高</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" /></el-form-item>
        <el-form-item label="检测提示"><el-input v-model="form.check_prompt" type="textarea" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
.head h2 { margin:0 0 4px; }
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.kpi .l { color:var(--zf-muted); font-size:13px; }
.kpi .v { font-size:28px; font-weight:700; margin:6px 0; }
.kpi .f { font-size:12px; color:var(--zf-muted); }
.radar { margin-top:16px; max-width:420px; }
.radar h4 { margin:0 0 10px; font-size:13px; }
.hbar { margin-bottom:8px; }
.hbar .top { display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px; }
.track { height:8px; background:#eef1f7; border-radius:99px; overflow:hidden; }
.track i { display:block; height:100%; background:#4f46e5; }
.review { display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--zf-line); gap:12px; }
@media (max-width:900px){ .kpi-grid { grid-template-columns:1fr 1fr; } }
</style>
