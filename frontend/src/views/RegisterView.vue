<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: '', password: '', nickname: '' })

async function submit() {
  if (form.username.length < 3 || form.password.length < 6) {
    ElMessage.warning('用户名至少 3 位，密码至少 6 位')
    return
  }
  loading.value = true
  try {
    await userStore.register(form.username, form.password, form.nickname || form.username)
    ElMessage.success('注册成功')
    router.replace('/workspace')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="card">
      <div class="mark">智服云</div>
      <h2>注册坐席账号</h2>
      <p class="hint">注册后可进入客服工作台与知识库</p>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="至少 3 位" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-button type="primary" class="full" :loading="loading" native-type="submit">注册并登录</el-button>
      </el-form>
      <div class="foot">已有账号？ <router-link to="/login">去登录</router-link></div>
    </div>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100%; display: grid; place-items: center; padding: 24px;
  background:
    radial-gradient(800px 400px at 80% 0%, rgba(61,79,216,0.14), transparent 60%),
    linear-gradient(160deg, #eef1f7, #f7f9fc);
}
.card {
  width: min(420px, 100%); background: #fff; border-radius: 18px; padding: 32px;
  border: 1px solid var(--zf-line);
}
.mark { font-size: 22px; font-weight: 700; margin-bottom: 18px; }
h2 { margin: 0 0 6px; }
.hint { color: var(--zf-muted); margin: 0 0 20px; font-size: 13px; }
.full { width: 100%; height: 40px; }
.foot { margin-top: 16px; font-size: 13px; color: var(--zf-muted); }
.foot a { color: var(--zf-primary); }
</style>
