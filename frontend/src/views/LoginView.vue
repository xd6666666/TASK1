<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })

async function submit() {
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.replace((route.query.redirect as string) || '/workspace')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="panel">
      <div class="hero">
        <div class="mark">智服云</div>
        <h1>电商智能客服系统</h1>
        <p>多渠道会话接入，知识驱动问答智能体，人工确认后发送。</p>
      </div>
      <div class="form-wrap">
        <h2>登录</h2>
        <p class="hint">演示账号 admin / admin123 或自行注册</p>
        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
          </el-form-item>
          <el-button type="primary" class="full" :loading="loading" native-type="submit">登录</el-button>
        </el-form>
        <div class="foot">还没有账号？ <router-link to="/register">注册</router-link></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100%;
  display: grid; place-items: center;
  padding: 24px;
  background:
    radial-gradient(900px 420px at 10% 0%, rgba(61,79,216,0.18), transparent 60%),
    radial-gradient(700px 380px at 90% 100%, rgba(13,148,148,0.16), transparent 55%),
    linear-gradient(160deg, #e8ecf6, #f5f7fb 45%, #e9f4f3);
}
.panel {
  width: min(920px, 100%);
  display: grid; grid-template-columns: 1.05fr 0.95fr;
  background: #fff; border-radius: 20px; overflow: hidden;
  border: 1px solid var(--zf-line); box-shadow: 0 24px 60px rgba(28, 39, 71, 0.08);
}
.hero {
  padding: 42px 36px;
  background: linear-gradient(160deg, #141b2d, #243056 55%, #1d4e5a);
  color: #fff;
}
.mark {
  display: inline-block; font-size: 28px; font-weight: 700; letter-spacing: 0.04em;
  margin-bottom: 28px;
}
.hero h1 { margin: 0 0 12px; font-size: 28px; line-height: 1.25; }
.hero p { margin: 0; opacity: 0.75; line-height: 1.7; max-width: 28em; }
.form-wrap { padding: 42px 36px; }
.form-wrap h2 { margin: 0 0 6px; }
.hint { color: var(--zf-muted); margin: 0 0 22px; font-size: 13px; }
.full { width: 100%; margin-top: 8px; height: 40px; }
.foot { margin-top: 18px; font-size: 13px; color: var(--zf-muted); }
.foot a { color: var(--zf-primary); }
@media (max-width: 800px) {
  .panel { grid-template-columns: 1fr; }
  .hero { display: none; }
}
</style>
