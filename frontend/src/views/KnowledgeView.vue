<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import {
  createFaq,
  deleteDocument,
  deleteFaq,
  documentFileUrl,
  getDocument,
  listDocuments,
  listFaqs,
  updateFaq,
  uploadDocument,
} from '@/api/knowledge'

const tab = ref('faq')
const faqLoading = ref(false)
const docLoading = ref(false)
const faqs = ref<any[]>([])
const docs = ref<any[]>([])
const faqTotal = ref(0)
const docTotal = ref(0)
const faqQuery = ref('')
const docQuery = ref('')
const faqPage = ref(1)
const docPage = ref(1)

const faqDialog = ref(false)
const faqEditingId = ref<number | null>(null)
const faqForm = reactive({
  question: '',
  answer: '',
  similar_text: '',
  status: 'published',
})

const detailVisible = ref(false)
const detailDoc = ref<any>(null)
const detailChunks = ref<any[]>([])

async function loadFaqs() {
  faqLoading.value = true
  try {
    const res: any = await listFaqs({ q: faqQuery.value, page: faqPage.value, page_size: 10 })
    faqs.value = res.data.list
    faqTotal.value = res.data.total
  } finally {
    faqLoading.value = false
  }
}

async function loadDocs() {
  docLoading.value = true
  try {
    const res: any = await listDocuments({ q: docQuery.value, page: docPage.value, page_size: 10 })
    docs.value = res.data.list
    docTotal.value = res.data.total
  } finally {
    docLoading.value = false
  }
}

function openCreateFaq() {
  faqEditingId.value = null
  faqForm.question = ''
  faqForm.answer = ''
  faqForm.similar_text = ''
  faqForm.status = 'published'
  faqDialog.value = true
}

function openEditFaq(row: any) {
  faqEditingId.value = row.id
  faqForm.question = row.question
  faqForm.answer = row.answer
  faqForm.similar_text = (row.similar_questions || []).join('\n')
  faqForm.status = row.status
  faqDialog.value = true
}

async function saveFaq() {
  const payload = {
    question: faqForm.question,
    answer: faqForm.answer,
    similar_questions: faqForm.similar_text
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean),
    status: faqForm.status,
  }
  if (faqEditingId.value) {
    await updateFaq(faqEditingId.value, payload)
    ElMessage.success('FAQ 已更新')
  } else {
    await createFaq(payload)
    ElMessage.success('FAQ 已创建')
  }
  faqDialog.value = false
  await loadFaqs()
}

async function removeFaq(row: any) {
  await ElMessageBox.confirm(`确认删除「${row.question}」？`, '删除 FAQ', { type: 'warning' })
  await deleteFaq(row.id)
  ElMessage.success('已删除')
  await loadFaqs()
}

async function customUpload(opt: UploadRequestOptions) {
  const form = new FormData()
  form.append('file', opt.file)
  form.append('title', opt.file.name)
  try {
    await uploadDocument(form)
    ElMessage.success('上传并分片索引完成')
    opt.onSuccess?.({} as any)
    await loadDocs()
  } catch (e) {
    opt.onError?.(e as any)
  }
}

async function openDoc(row: any) {
  const res: any = await getDocument(row.id)
  detailDoc.value = res.data.document
  detailChunks.value = res.data.chunks || []
  detailVisible.value = true
}

function previewOriginal() {
  if (!detailDoc.value) return
  const token = localStorage.getItem('zf_token') || ''
  // open via fetch blob to attach auth header
  fetch(documentFileUrl(detailDoc.value.id), {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((r) => r.blob())
    .then((blob) => {
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    })
}

async function removeDoc(row: any) {
  await ElMessageBox.confirm(`确认删除文档「${row.title}」？`, '删除文档', { type: 'warning' })
  await deleteDocument(row.id)
  ElMessage.success('已删除')
  await loadDocs()
}

onMounted(() => {
  loadFaqs()
  loadDocs()
})
</script>

<template>
  <div>
    <div class="head page-card">
      <div>
        <h2>知识库管理</h2>
        <p class="muted">维护 FAQ（含相似问）与 Word/PDF 文档；上传后自动分片并写入向量库，供问答智能体召回。</p>
      </div>
      <div class="acts">
        <el-button v-if="tab === 'faq'" type="primary" @click="openCreateFaq">新建 FAQ</el-button>
        <el-upload
          v-else
          :show-file-list="false"
          :http-request="customUpload"
          accept=".pdf,.doc,.docx,.txt,.md"
        >
          <el-button type="primary">上传文档</el-button>
        </el-upload>
      </div>
    </div>

    <div class="page-card" style="margin-top: 12px">
      <el-tabs v-model="tab">
        <el-tab-pane label="FAQ 问答" name="faq">
          <div class="toolbar">
            <el-input
              v-model="faqQuery"
              placeholder="搜索问题 / 答案 / 相似问"
              clearable
              style="max-width: 320px"
              @keyup.enter="loadFaqs"
              @clear="loadFaqs"
            />
            <el-button @click="loadFaqs">查询</el-button>
          </div>
          <el-table :data="faqs" v-loading="faqLoading" stripe>
            <el-table-column prop="question" label="问题" min-width="180" />
            <el-table-column prop="answer" label="答案" min-width="240" show-overflow-tooltip />
            <el-table-column label="相似问" min-width="160">
              <template #default="{ row }">
                <el-tag
                  v-for="(s, i) in (row.similar_questions || []).slice(0, 3)"
                  :key="i"
                  size="small"
                  class="sim"
                  effect="plain"
                >{{ s }}</el-tag>
                <span v-if="!(row.similar_questions || []).length" class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
                  {{ row.status === 'published' ? '已发布' : '草稿' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEditFaq(row)">编辑</el-button>
                <el-button link type="danger" @click="removeFaq(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager">
            <el-pagination
              v-model:current-page="faqPage"
              layout="total, prev, pager, next"
              :page-size="10"
              :total="faqTotal"
              @current-change="loadFaqs"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="文档知识" name="doc">
          <div class="toolbar">
            <el-input
              v-model="docQuery"
              placeholder="搜索标题 / 文件名"
              clearable
              style="max-width: 320px"
              @keyup.enter="loadDocs"
              @clear="loadDocs"
            />
            <el-button @click="loadDocs">查询</el-button>
            <span class="muted">支持 PDF / Word(docx) / txt / md，上传后自动分片入库</span>
          </div>
          <el-table :data="docs" v-loading="docLoading" stripe>
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column prop="filename" label="原始文件" min-width="160" />
            <el-table-column prop="chunk_count" label="分片数" width="90" />
            <el-table-column prop="status" label="索引状态" width="110">
              <template #default="{ row }">
                <el-tag
                  size="small"
                  :type="row.status === 'ready' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'"
                >
                  {{ row.status === 'ready' ? '已就绪' : row.status === 'failed' ? '失败' : '处理中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="summary" label="摘要" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDoc(row)">分片/预览</el-button>
                <el-button link type="danger" @click="removeDoc(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager">
            <el-pagination
              v-model:current-page="docPage"
              layout="total, prev, pager, next"
              :page-size="10"
              :total="docTotal"
              @current-change="loadDocs"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="faqDialog" :title="faqEditingId ? '编辑 FAQ' : '新建 FAQ'" width="640px">
      <el-form label-position="top">
        <el-form-item label="问题" required>
          <el-input v-model="faqForm.question" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="faqForm.answer" type="textarea" :rows="5" />
        </el-form-item>
        <el-form-item label="相似问（每行一条）">
          <el-input v-model="faqForm.similar_text" type="textarea" :rows="4" placeholder="退款什么时候到&#10;钱什么时候退回来" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="faqForm.status">
            <el-radio value="published">发布并索引</el-radio>
            <el-radio value="draft">草稿</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="faqDialog = false">取消</el-button>
        <el-button type="primary" @click="saveFaq">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" size="520px" :title="detailDoc?.title || '文档详情'">
      <div v-if="detailDoc">
        <el-button type="primary" plain @click="previewOriginal">预览原始文件</el-button>
        <p class="muted" style="margin: 12px 0">文件：{{ detailDoc.filename }} · 分片 {{ detailDoc.chunk_count }}</p>
        <el-divider>分片预览</el-divider>
        <div v-for="c in detailChunks" :key="c.id" class="chunk">
          <div class="chunk-h">#{{ c.chunk_index + 1 }}</div>
          <pre>{{ c.content }}</pre>
        </div>
        <el-empty v-if="!detailChunks.length" description="暂无分片" />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.head h2 { margin: 0 0 6px; font-size: 18px; }
.head p { margin: 0; max-width: 52em; }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.pager { display: flex; justify-content: flex-end; margin-top: 14px; }
.sim { margin: 0 4px 4px 0; }
.chunk {
  border: 1px solid var(--zf-line); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px;
  background: #fafbfe;
}
.chunk-h { font-size: 12px; color: var(--zf-muted); margin-bottom: 6px; }
.chunk pre {
  margin: 0; white-space: pre-wrap; font-family: inherit; font-size: 13px; line-height: 1.55;
}
</style>
