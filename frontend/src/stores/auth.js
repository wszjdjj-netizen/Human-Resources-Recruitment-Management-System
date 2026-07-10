import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, getMe, logout as logoutApi, updateMe } from '../api/auth'

const TOKEN_KEY = 'auth_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const checked = ref(false)

  function persistToken(t) {
    if (t) {
      localStorage.setItem(TOKEN_KEY, t)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
    token.value = t
  }

  const isLoggedIn = computed(() => !!token.value || !!user.value)
  const username = computed(() => user.value?.username || '')
  const companyName = computed(() => user.value?.company_name || '')

  async function login(username, password) {
    const res = await loginApi(username, password)
    persistToken(res.token || '')
    user.value = { id: res.id, username: res.username, email: res.email, company_name: res.company_name }
    checked.value = true
    return res
  }

  async function register(data) {
    const res = await registerApi(data)
    persistToken(res.token || '')
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
      clearClientAuth()
      checked.value = true
      return false
    }
  }

  async function ensureAuth() {
    if (checked.value) return !!user.value
    return fetchMe()
  }

  function clearClientAuth() {
    persistToken('')
    user.value = null
  }

  async function logout() {
    clearClientAuth()
    checked.value = true
    try {
      await logoutApi()
    } catch { }
  }

  async function updateProfile(data) {
    const res = await updateMe(data)
    user.value = res
    return res
  }

  return {
    user, token, checked, isLoggedIn, username, companyName,
    login, register, fetchMe, ensureAuth, updateProfile, logout
  }
})
