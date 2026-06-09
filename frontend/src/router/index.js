import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    component: () => import('../views/LayoutView.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/DashboardView.vue')
      },
      {
        path: 'positions',
        name: 'Positions',
        component: () => import('../views/PositionListView.vue')
      },
      {
        path: 'positions/create',
        name: 'PositionCreate',
        component: () => import('../views/PositionFormView.vue')
      },
      {
        path: 'positions/:id',
        name: 'PositionDetail',
        component: () => import('../views/PositionDetailView.vue')
      },
      {
        path: 'positions/:id/edit',
        name: 'PositionEdit',
        component: () => import('../views/PositionFormView.vue')
      },
      {
        path: 'talent-pool',
        name: 'TalentPool',
        component: () => import('../views/TalentPoolView.vue')
      },
      {
        path: 'candidates/:id',
        name: 'CandidateDetail',
        component: () => import('../views/CandidateDetailView.vue')
      },
      {
        path: 'ai-config',
        name: 'AiConfig',
        component: () => import('../views/AiConfigView.vue')
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/ProfileView.vue')
      },
      {
        path: 'sourcing',
        name: 'SourcingDemo',
        component: () => import('../views/SourcingDemoView.vue')
      },
      {
        path: 'workflow-match',
        name: 'WorkflowMatch',
        component: () => import('../views/WorkflowMatchView.vue')
      },
      {
        path: 'interviews',
        name: 'Interviews',
        component: () => import('../views/InterviewListView.vue')
      },
      {
        path: 'interviews/:id',
        name: 'InterviewDetail',
        component: () => import('../views/InterviewLiveView.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 导航守卫：检查登录状态
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !(await authStore.ensureAuth())) {
    // 需要登录但未登录 → 跳转登录页
    next('/login')
  } else if (to.meta.guest && (await authStore.ensureAuth())) {
    // 已登录但访问游客页面 → 跳转首页
    next('/')
  } else {
    next()
  }
})

export default router
