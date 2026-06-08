import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { useAuthStore } from '../stores/auth'

const runtimeConfig = window.__APP_CONFIG__ || {}

const request = axios.create({
  baseURL: runtimeConfig.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
  withCredentials: true
})

request.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const { response, config } = error

    // 判断是否跳过统一错误提示（由调用方自己处理）
    const silent = config?.silent === true
    const authStore = useAuthStore()

    if (response) {
      const detail = response.data?.detail
      switch (response.status) {
        case 401: {
          // 避免对登录/注册接口本身返回的 401 也触发登出
          const isAuthEndpoint = (config?.url || '').includes('/auth/')
          if (!isAuthEndpoint) {
            // 用 router 软跳到登录页，避免整页刷新导致白屏
            ElMessage.error('登录已过期，请重新登录')
            authStore.logout()
            const currentPath = router?.currentRoute?.value?.fullPath || '/'
            if (router && !currentPath.startsWith('/login')) {
              try {
                router.push(`/login?redirect=${encodeURIComponent(currentPath)}`)
              } catch (e) {
                // 路由不可用时再降级到硬跳
                window.location.href = '/login'
              }
            }
          }
          break
        }
        case 403:
          if (!silent) ElMessage.error('没有权限执行此操作')
          break
        case 404:
          if (!silent) ElMessage.error(detail || `请求的资源不存在：${config?.url || ''}`)
          break
        case 422:
          if (!silent) {
            if (Array.isArray(detail)) {
              ElMessage.error(detail[0]?.msg || '参数错误')
            } else {
              ElMessage.error(detail || '参数错误')
            }
          }
          break
        case 500:
          if (!silent) ElMessage.error(detail || '服务器内部错误，请稍后重试')
          break
        default:
          if (!silent) ElMessage.error(detail || `请求失败 (${response.status})`)
      }
    } else if (!silent) {
      // 网络/连接错误：给更友好的提示，并提供诊断链接
      console.error('[API 错误] 详情:', error)
      ElMessage.error({
        message: '无法连接到后端服务，请检查后端是否已启动（端口 8000）',
        duration: 5000,
      })
    }
    return Promise.reject(error)
  }
)

export default request
