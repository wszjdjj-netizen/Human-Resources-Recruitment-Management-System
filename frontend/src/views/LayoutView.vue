<template>
  <div class="layout-container">
    <!-- 侧边导航 -->
    <el-menu
      :default-active="activeMenu"
      class="side-nav"
      background-color="transparent"
      text-color="rgba(31, 45, 61, 0.76)"
      active-text-color="#1f2d3d"
      router
      :collapse="false"
    >
      <div class="logo-area">
        <h2>招聘管理系统</h2>
      </div>
      <el-menu-item index="/">
        <el-icon><DataAnalysis /></el-icon>
        <span>首页概览</span>
      </el-menu-item>
      <el-menu-item index="/positions">
        <el-icon><Briefcase /></el-icon>
        <span>职位管理</span>
      </el-menu-item>
      <el-menu-item index="/talent-pool">
        <el-icon><UserFilled /></el-icon>
        <span>人才池</span>
      </el-menu-item>
      <el-menu-item index="/ai-config">
        <el-icon><Setting /></el-icon>
        <span>AI配置</span>
      </el-menu-item>
      <el-menu-item index="/sourcing">
        <el-icon><Aim /></el-icon>
        <span>平台搜人</span>
      </el-menu-item>
      <el-menu-item index="/workflow-match">
        <el-icon><MagicStick /></el-icon>
        <span>工作流匹配</span>
      </el-menu-item>
      <el-menu-item index="/interviews">
        <el-icon><VideoCamera /></el-icon>
        <span>面试管理</span>
      </el-menu-item>
      <el-menu-item index="/profile">
        <el-icon><User /></el-icon>
        <span>个人资料</span>
      </el-menu-item>
    </el-menu>

    <!-- 主内容区 -->
    <div class="main-area">
      <!-- 顶部栏 -->
      <div class="top-bar">
        <div class="top-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="pageTitle">{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="top-right">
          <el-button text class="profile-link" @click="router.push('/profile')">
            <el-icon><User /></el-icon>
            <span>{{ authStore.username }}</span>
          </el-button>
          <el-button text @click="handleLogout">退出登录</el-button>
        </div>
      </div>

      <!-- 页面内容 -->
      <div class="page-content">
        <ErrorBoundary>
          <router-view />
        </ErrorBoundary>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ErrorBoundary from '../components/ErrorBoundary.vue'
import {
  DataAnalysis, Briefcase, UserFilled, Setting, Aim, MagicStick, User, VideoCamera
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 当前活跃菜单项
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/positions')) return '/positions'
  if (path.startsWith('/talent-pool')) return '/talent-pool'
  if (path.startsWith('/candidates')) return '/talent-pool'
  if (path.startsWith('/ai-config')) return '/ai-config'
  if (path.startsWith('/sourcing')) return '/sourcing'
  if (path.startsWith('/workflow-match')) return '/workflow-match'
  if (path.startsWith('/interviews')) return '/interviews'
  if (path.startsWith('/profile')) return '/profile'
  return path
})

// 页面标题（用于面包屑）
const pageTitle = computed(() => {
  const map = {
    '/': '',
    '/positions': '职位管理',
    '/talent-pool': '人才池',
    '/ai-config': 'AI配置',
    '/sourcing': '平台搜人',
    '/workflow-match': '工作流匹配',
    '/interviews': '面试管理',
    '/profile': '个人资料'
  }
  if (route.path.startsWith('/positions/create')) return '新建职位'
  if (route.path.includes('/edit')) return '编辑职位'
  if (route.path.startsWith('/positions/')) return '职位详情'
  if (route.path.startsWith('/candidates/')) return '候选人详情'
  if (route.path.startsWith('/interviews/')) return '面试详情'
  return map[route.path] || ''
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

</script>

<style scoped>
.layout-container {
  display: flex;
  min-height: 100vh;
  padding: 18px;
  gap: 18px;
}

.side-nav {
  width: 230px;
  min-height: 100vh;
  flex-shrink: 0;
  border-right: none;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: 12px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(241, 247, 255, 0.82)),
    rgba(247, 250, 255, 0.92);
  box-shadow: 0 24px 60px rgba(11, 19, 36, 0.18);
  backdrop-filter: blur(20px) saturate(1.08);
}

.logo-area {
  padding: 24px 18px;
  text-align: center;
  border-bottom: 1px solid rgba(78, 92, 130, 0.08);
  margin-bottom: 12px;
}

.logo-area h2 {
  color: #1f2d3d;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.005em;
  margin: 0;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(245, 249, 255, 0.62);
  box-shadow: 0 24px 60px rgba(45, 65, 98, 0.12);
  backdrop-filter: blur(16px);
}

.top-bar {
  height: 60px;
  background: rgba(255, 255, 255, 0.78);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  border-bottom: 1px solid rgba(78, 92, 130, 0.08);
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  backdrop-filter: blur(18px);
}

.top-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.profile-link {
  color: #344054;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0;
}

.profile-link:hover {
  color: #2f63ff;
}

.page-content {
  flex: 1;
  padding: 8px;
  background:
    linear-gradient(135deg, rgba(255,255,255,0.26), transparent 36%),
    linear-gradient(180deg, rgba(244, 249, 255, 0.96), rgba(238, 245, 255, 0.92));
  overflow-y: auto;
}

:deep(.el-menu) {
  border-right: none;
  background: transparent;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: rgba(31, 45, 61, 0.72);
  font-weight: 500;
}

:deep(.el-menu-item) {
  margin: 6px 12px;
  border-radius: 10px;
  height: 48px;
  transition: background-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

:deep(.el-menu-item.is-active) {
  color: #1f2d3d;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(79, 124, 255, 0.16), rgba(18, 182, 203, 0.1));
  box-shadow: inset 0 0 0 1px rgba(79, 124, 255, 0.08), 0 10px 26px rgba(14, 29, 58, 0.1);
}

:deep(.el-menu-item:hover) {
  color: #1f2d3d;
  background: rgba(79, 124, 255, 0.08);
  transform: translateX(1px);
}

:deep(.el-menu-item .el-icon),
:deep(.el-sub-menu__title .el-icon) {
  color: inherit;
}

@media (max-width: 920px) {
  .layout-container {
    padding: 0;
    flex-direction: column;
    gap: 0;
  }

  .side-nav {
    width: 100%;
    min-height: auto;
    border-radius: 0;
  }

  .main-area {
    border-radius: 0;
  }
}
</style>
