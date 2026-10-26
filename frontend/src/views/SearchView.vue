<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { searchQuery } from '@/api/search'

const query = ref('退款多久能到账')
const mode = ref('hybrid')
const threshold = ref(0.3)
const topK = ref(5)
const loading = ref(false)
const result = ref<any>(null)

async function run(feedback?: string) {
  if (!query.value.trim()) return
  loading.value = true
  try {
    const res: any = await searchQuery({
      query: query.value.trim(),
      mode: mode.value,
      threshold: threshold.value,
      top_k: topK.value,
      feedback,
    })
    result.value = res.data
    if (feedback) ElMessage.success('反馈已记录')
  } finally {
    loading.value = false
  }
}

run()
</script>

<template>
  <div>
    <div class="page-card hero">
      <h2>知识查询</h2>
      <p class="muted">语义检索 + 关键词混合召回，验证知识覆盖与答案质量。</p>
      <div class="box">
        <el-input v-model="query" size="large" placeholder="输入客户问题" @keyup.enter="run()" />
        <el-button type="primary" size="large" :loading="loading" @click="run()">查询</el-button>
      </div>
      <div class="modes">
        <el-radio-group v-model="mode" @change="run()">
          <el-radio-button value="hybrid">混合检索</el-radio-button>
          <el-radio-button value="semantic">语义检索</el-radio-button>
          <el-radio-button value="keyword">关键词</el-radio-button>
        </el-radio-group>
        <span class="muted" v-if="result?.stats">
          召回 {{ result.stats.recall }} · 耗时 {{ result.stats.elapsed_ms }}ms · 均分 {{ result.stats.avg_score }}
          <el-tag v-if="result.mock" size="small" type="warning" style="margin-left:8px">Mock</el-tag>
        </span>
      </div>
    </div>

    <div class="layout" v-loading="loading">
      <div class="page-card">
        <div class="answer" v-if="result">
          <div class="ah"><el-icon><MagicStick /></el-icon> AI 聚合答案</div>
          <p>{{ result.answer }}</p>
          <div class="cites">
            <span class="muted">引用来源：</span>
            <el-tag v-for="(c, i) in result.citations || []" :key="i" size="small" effect="plain">{{ c.title }}</el-tag>
          </div>
        </div>
        <h3>召回结果</h3>
        <div v-for="(item, idx) in result?.items || []" :key="idx" class="hit">
          <div class="ht">
            <strong>{{ item.title }}</strong>
            <el-tag size="small">{{ item.via }}</el-tag>
            <span class="score">{{ Number(item.score).toFixed(3) }}</span>
          </div>
          <pre>{{ item.text }}</pre>
        </div>
        <el-empty v-if="result && !(result.items || []).length" description="无召回" />
      </div>

      <div class="page-card side">
        <h3>检索调试</h3>
        <div class="row"><span>相似度阈值</span><b>{{ threshold }}</b></div>
        <el-slider v-model="threshold" :min="0" :max="0.95" :step="0.01" @change="run()" />
        <div class="row"><span>Top K</span>
          <el-input-number v-model="topK" :min="1" :max="20" size="small" @change="run()" />
        </div>
        <div class="row"><span>向量召回</span><b>{{ result?.stats?.semantic_count ?? '-' }}</b></div>
        <div class="row"><span>关键词召回</span><b>{{ result?.stats?.keyword_count ?? '-' }}</b></div>
        <el-divider />
        <div class="row"><span>本次评价</span></div>
        <div class="acts">
          <el-button size="small" @click="run('good')">有帮助</el-button>
          <el-button size="small" @click="run('bad')">需优化</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero h2 { margin: 0 0 6px; }
.box { display: flex; gap: 10px; margin: 14px 0 10px; }
.modes { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.layout { display: grid; grid-template-columns: 1.6fr 0.9fr; gap: 12px; margin-top: 12px; }
.answer { background: #f7f8ff; border: 1px dashed #b7c0ff; border-radius: 12px; padding: 12px; margin-bottom: 14px; }
.ah { font-weight: 650; display: flex; gap: 6px; align-items: center; margin-bottom: 8px; }
.answer p { margin: 0; white-space: pre-wrap; line-height: 1.6; }
.cites { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
h3 { margin: 0 0 10px; font-size: 14px; }
.hit { border: 1px solid var(--zf-line); border-radius: 10px; padding: 10px; margin-bottom: 10px; background: #fafbfe; }
.ht { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.score { margin-left: auto; color: var(--zf-muted); font-size: 12px; }
.hit pre { margin: 0; white-space: pre-wrap; font-family: inherit; font-size: 13px; line-height: 1.5; }
.side .row { display: flex; justify-content: space-between; align-items: center; margin: 10px 0; font-size: 13px; }
.acts { display: flex; gap: 8px; }
@media (max-width: 960px) { .layout { grid-template-columns: 1fr; } }
</style>
