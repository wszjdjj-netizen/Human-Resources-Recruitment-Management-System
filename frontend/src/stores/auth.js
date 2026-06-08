import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, getMe, logout as logoutApi, updateMe } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref(null)
  const token = ref('')
  const checked = ref(false)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value || !!user.value)
  const username = computed(() => user.value?.username || '')
  const companyName = computed(() => user.value?.company_name || '')

  // 行动
  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = ''
    user.value = { id: res.id, username: res.username, email: res.email, company_name: res.company_name }
    checked.value = true
    return res
  }

  async function register(data) {
    const res = await registerApi(data)
    token.value = ''
    user.value = { id: res.id, username: res.username, email: res.email, company_name: res.company_name }
    checked.value = true
    return res
  }

  async function fetchMe() {
    try {
      const res = await getMe()
      user.value = res
      checked.value = true
      return true
    } catch {
      // token过期或无效，清除登录状态
      clearClientAuth()
      checked.value = true
      return false
    }
  }

  async function ensureAuth() {
    if (isLoggedIn.value) return true
    if (checked.value) return false
    return fetchMe()
  }

  function clearClientAuth() {
    token.value = ''
    user.value = null
  }

  async function logout() {
    clearClientAuth()
    checked.value = true
    try {
      await logoutApi()
    } catch {
      // 本地状态已经清理，服务端清理失败不阻塞退出
    }
  }

  async function updateProfile(data) {
    const res = await updateMe(data)
    user.value = res
    return res
  }

  return {
    user,
    token,
    checked,
    isLoggedIn,
    username,
    companyName,
    login,
    register,
    fetchMe,
    ensureAuth,
    updateProfile,
    logout
  }
})
