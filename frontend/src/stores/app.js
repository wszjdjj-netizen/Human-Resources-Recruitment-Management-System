import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 全局加载状态
  const loading = ref(false)
  // AI是否已配置
  const aiConfigured = ref(false)

  function setLoading(val) {
    loading.value = val
  }

  function setAiConfigured(val) {
    aiConfigured.value = val
  }

  return {
    loading,
    aiConfigured,
    setLoading,
    setAiConfigured
  }
})
