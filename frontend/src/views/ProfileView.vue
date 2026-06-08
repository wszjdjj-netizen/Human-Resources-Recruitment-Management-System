<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header page-hero">
      <div>
        <span class="eyebrow">Account Profile</span>
        <h2>个人资料</h2>
        <p class="text-muted">修改用户名、邮箱、公司信息，支持同步更新登录后的展示信息。</p>
      </div>
    </div>

    <el-card class="glass-card profile-shell">
      <el-form :model="form" label-width="110px" size="large">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="公司名称">
          <el-input v-model="form.company_name" placeholder="可选" />
        </el-form-item>

        <el-divider content-position="left">修改密码</el-divider>
        <el-form-item label="当前密码">
          <el-input v-model="form.current_password" type="password" show-password placeholder="如不修改密码可留空" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="form.new_password" type="password" show-password placeholder="至少8位，含字母和数字" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存资料</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const loading = ref(true)
const saving = ref(false)

const form = reactive({
  username: '',
  email: '',
  company_name: '',
  current_password: '',
  new_password: ''
})

async function syncForm() {
  loading.value = true
  try {
    if (!authStore.user) {
      await authStore.fetchMe()
    }
    form.username = authStore.user?.username || ''
    form.email = authStore.user?.email || ''
    form.company_name = authStore.user?.company_name || ''
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!form.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!form.email.trim()) {
    ElMessage.warning('请输入邮箱')
    return
  }
  if (form.new_password && form.new_password.length < 8) {
    ElMessage.warning('新密码至少8位')
    return
  }
  if (form.new_password && (!/[A-Za-z]/.test(form.new_password) || !/\d/.test(form.new_password))) {
    ElMessage.warning('新密码需同时包含字母和数字')
    return
  }

  saving.value = true
  try {
    await authStore.updateProfile({
      username: form.username,
      email: form.email,
      company_name: form.company_name,
      current_password: form.current_password || null,
      new_password: form.new_password || null
    })
    form.current_password = ''
    form.new_password = ''
    ElMessage.success('资料已更新')
  } catch {
    // 错误已由拦截器提示
  } finally {
    saving.value = false
  }
}

onMounted(syncForm)
</script>
