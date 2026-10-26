import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layout/MainLayout.vue'),
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '运营概览', sub: '智能客服全链路运营数据' },
        },
        {
          path: 'workspace',
          name: 'workspace',
          component: () => import('@/views/WorkspaceView.vue'),
          meta: { title: '客服工作台', sub: '多渠道接入 · AI 推荐 · 人工确认发送' },
        },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('@/views/KnowledgeView.vue'),
          meta: { title: '知识库管理', sub: 'FAQ 与文档统一供给智能体' },
        },
        {
          path: 'search',
          name: 'search',
          component: () => import('@/views/SearchView.vue'),
          meta: { title: '知识查询', sub: '语义检索 · 召回调试与效果分析' },
        },
        {
          path: 'qa',
          name: 'qa',
          component: () => import('@/views/QaView.vue'),
          meta: { title: '质检系统', sub: '全量自动质检 · 人工复核' },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { title: '系统设置', sub: '模型、渠道与团队配置' },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('zf_token')
  if (!to.meta.public && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if ((to.path === '/login' || to.path === '/register') && token) {
    return { path: '/dashboard' }
  }
  return true
})

export default router
