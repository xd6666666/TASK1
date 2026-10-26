<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const title = computed(() => (route.meta.title as string) || '')
const sub = computed(() => (route.meta.sub as string) || '')

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="logo">智</div>
        <div>
          <div class="brand-name">智服云</div>
          <div class="brand-sub">电商智能客服</div>
        </div>
      </div>
      <nav class="nav">
        <div class="nav-label">工作空间</div>
        <router-link class="nav-item" to="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>运营概览</span>
        </router-link>
        <router-link class="nav-item" to="/workspace">
          <el-icon><Headset /></el-icon>
          <span>客服工作台</span>
        </router-link>
        <div class="nav-label">知识中枢</div>
        <router-link class="nav-item" to="/knowledge">
          <el-icon><Collection /></el-icon>
          <span>知识库管理</span>
        </router-link>
        <router-link class="nav-item" to="/search">
          <el-icon><Search /></el-icon>
          <span>知识查询</span>
        </router-link>
        <div class="nav-label">质量管理</div>
        <router-link class="nav-item" to="/qa">
          <el-icon><Shield /></el-icon>
          <span>质检系统</span>
        </router-link>
        <div class="nav-label">系统</div>
        <router-link class="nav-item" to="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </router-link>
      </nav>
      <div class="side-foot">
        <div class="help">
          <strong>智服云</strong>
          <p>运营 · 工作台 · 知识 · 质检 · 设置</p>
        </div>
      </div>
    </aside>

    <div class="main">
      <header class="top">
        <div>
          <h1>{{ title }}</h1>
          <p>{{ sub }}</p>
        </div>
        <div class="top-right">
          <el-tag type="info" effect="plain">渠道：公众号 / 企微 / App / Web</el-tag>
          <el-dropdown>
            <button class="user">
              <span class="avatar">{{ (userStore.user?.nickname || '客')[0] }}</span>
              <span>
                <strong>{{ userStore.user?.nickname || userStore.user?.username }}</strong>
                <small>{{ userStore.user?.role === 'admin' ? '管理员' : '客服坐席' }}</small>
              </span>
              <el-icon><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell { display: grid; grid-template-columns: 232px 1fr; height: 100%; }
.side {
  background: linear-gradient(180deg, #141b2d 0%, #1a2238 100%);
  color: var(--zf-sidebar-text);
  display: flex; flex-direction: column; padding: 18px 14px;
}
.brand { display: flex; gap: 12px; align-items: center; padding: 4px 8px 20px; }
.logo {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, #5b6cff, #22b8b8);
  display: grid; place-items: center; color: #fff; font-weight: 700;
}
.brand-name { color: #fff; font-weight: 700; letter-spacing: 0.02em; }
.brand-sub { font-size: 12px; opacity: 0.65; margin-top: 2px; }
.nav { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.nav-label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
  opacity: 0.45; margin: 14px 8px 6px;
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 10px; color: inherit;
}
.nav-item.router-link-active,
.nav-item:hover { background: rgba(255,255,255,0.08); color: #fff; }
.side-foot { padding: 8px; }
.help {
  background: rgba(255,255,255,0.06); border-radius: 12px; padding: 12px;
  font-size: 12px; line-height: 1.5;
}
.help strong { color: #fff; display: block; margin-bottom: 4px; }
.help p { margin: 0; opacity: 0.7; }
.main { display: flex; flex-direction: column; min-width: 0; }
.top {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 22px; background: rgba(255,255,255,0.72);
  border-bottom: 1px solid var(--zf-line); backdrop-filter: blur(8px);
}
.top h1 { margin: 0; font-size: 20px; }
.top p { margin: 4px 0 0; color: var(--zf-muted); font-size: 13px; }
.top-right { display: flex; align-items: center; gap: 12px; }
.user {
  display: flex; align-items: center; gap: 10px; border: 0; background: transparent; cursor: pointer;
}
.user strong { display: block; font-size: 13px; text-align: left; }
.user small { color: var(--zf-muted); font-size: 11px; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--zf-primary-soft); color: var(--zf-primary);
  display: grid; place-items: center; font-weight: 700;
}
.content { flex: 1; overflow: auto; padding: 16px 18px 24px; }
@media (max-width: 900px) {
  .shell { grid-template-columns: 1fr; }
  .side { display: none; }
}
</style>
