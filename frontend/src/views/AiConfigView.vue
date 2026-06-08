<template>
  <div class="page-container">
    <div class="page-header page-hero ai-hero">
      <div>
        <span class="eyebrow">Model Control</span>
        <h2>AI接口配置</h2>
        <p class="text-muted">保存多套兼容 OpenAI 格式的模型配置，随时切换当前用于简历解析、岗位匹配和平台搜人的模型。</p>
      </div>
      <el-tag v-if="savedKey" type="success" effect="plain">已保存密钥</el-tag>
    </div>

    <div class="config-layout">
      <section class="config-main">
        <el-card class="glass-card config-panel">
          <template #header>
            <div class="panel-title">
              <strong>{{ form.id ? '编辑模型配置' : '新增模型配置' }}</strong>
              <span class="text-muted">API Key 已保存时可留空，只改模型或地址即可。</span>
            </div>
          </template>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="112px" size="large">
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="form.name" placeholder="如：DeepSeek 主账号" />
            </el-form-item>
            <el-form-item label="API地址" prop="endpoint">
              <el-input v-model="form.endpoint" placeholder="如：https://api.deepseek.com/v1" />
              <div class="text-muted helper">请输入完整基础地址，通常以 /v1 结尾。线上默认拒绝 localhost/内网地址。</div>
            </el-form-item>
            <el-form-item label="API密钥" :prop="savedKey ? '' : 'api_key'">
              <el-input v-model="form.api_key" type="password" show-password :placeholder="savedKey ? '已保存，可留空继续使用原密钥' : '请输入 API Key'" />
            </el-form-item>
            <el-form-item label="模型名称" prop="model">
              <el-input v-model="form.model" placeholder="如：deepseek-chat、qwen-plus、gpt-4o" />
            </el-form-item>

            <el-divider content-position="left">解析模式</el-divider>
            <el-form-item label="解析模式">
              <el-radio-group v-model="form.parsing_mode">
                <el-radio value="generic">通用解析</el-radio>
                <el-radio value="custom">按岗位定制</el-radio>
              </el-radio-group>
              <div class="text-muted helper">
                按岗位定制会使用职位里的 AI 解析提示词；未设置时自动退回通用解析。
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSave">保存并启用</el-button>
              <el-button type="success" :loading="testing" @click="handleTest">测试当前配置</el-button>
              <el-button @click="resetForm">新建配置</el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="testResult"
            :title="testResult.success ? `连接成功，延迟 ${testResult.latency}ms` : testResult.error"
            :type="testResult.success ? 'success' : 'error'"
            show-icon
            style="margin-top: 16px;"
          />
        </el-card>

        <el-card class="glass-card">
          <template #header><strong>推荐配置</strong></template>
          <el-table :data="presets" size="small">
            <el-table-column prop="name" label="服务商" width="120" />
            <el-table-column prop="endpoint" label="API地址" min-width="260" />
            <el-table-column prop="model" label="推荐模型" width="170" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button size="small" @click="applyPreset(row)">填入</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </section>

      <aside class="config-side">
        <el-card class="glass-card">
          <template #header><strong>已保存配置</strong></template>
          <div v-if="!providers.length" class="empty-mini">暂无配置</div>
          <div v-for="item in providers" :key="item.id" class="provider-item" :class="{ active: item.is_active }">
            <div class="provider-info">
              <div class="provider-info__head">
                <strong>{{ item.name }}</strong>
                <el-tag size="small" :type="item.has_key ? 'success' : 'warning'" effect="plain">
                  {{ item.has_key ? '有密钥' : '缺密钥' }}
                </el-tag>
                <el-tag v-if="item.is_active" size="small" type="primary" effect="plain">当前启用</el-tag>
              </div>
              <div class="text-muted provider-model">{{ item.model }}</div>
              <div class="provider-endpoint" :title="item.endpoint">{{ item.endpoint }}</div>
            </div>
            <div class="provider-actions">
              <el-button size="small" @click.stop="editProvider(item)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="primary" plain :disabled="item.is_active" @click.stop="activateProvider(item)">
                <el-icon><Check /></el-icon>
                启用
              </el-button>
              <el-button size="small" type="danger" plain :disabled="providers.length <= 1" @click.stop="removeProvider(item)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </div>
        </el-card>

        <el-card class="glass-card usage-card">
          <template #header><strong>调用说明</strong></template>
          <div class="usage-list">
            <div>1. 这里保存的是后端真实调用模型所需的地址、Key 和模型名。</div>
            <div>2. 已保存的 Key 不会明文回显，所以页面显示“已保存密钥”是正常的。</div>
            <div>3. 更换模型时直接改“模型名称”并保存，不需要删除 Key。</div>
            <div>4. 平台搜人当前使用演示适配器，真实抓取还需要平台授权或第三方数据 API。</div>
          </div>
        </el-card>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Delete, Edit } from '@element-plus/icons-vue'
import { activateAiConfig, deleteAiConfig, getAiConfig, testAiConnection, updateAiConfig } from '../api/aiConfig'

const KEEP_KEY = '__KEEP_SAVED_KEY__'
const formRef = ref(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const providers = ref([])
const activeId = ref('')

const form = reactive({
  id: '',
  name: 'DeepSeek',
  endpoint: 'https://api.deepseek.com/v1',
  api_key: '',
  model: 'deepseek-chat',
  parsing_mode: 'generic',
  has_key: false
})

const savedKey = computed(() => form.has_key)

const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入API地址', trigger: 'blur' }],
  api_key: [{
    validator: (_, value, callback) => {
      if (form.has_key || value?.trim()) callback()
      else callback(new Error('请输入API密钥'))
    },
    trigger: 'blur'
  }],
  model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}

const presets = [
  { id: 'deepseek', name: 'DeepSeek', endpoint: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  { id: 'qwen', name: '通义千问', endpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  { id: 'openai', name: 'OpenAI', endpoint: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { id: 'ollama', name: '本地Ollama', endpoint: 'http://localhost:11434/v1', model: 'qwen2.5' }
]

function fillFromConfig(config) {
  activeId.value = config.active_id
  providers.value = config.providers || []
  form.id = config.active_id || ''
  form.name = providers.value.find((item) => item.id === config.active_id)?.name || '默认配置'
  form.endpoint = config.endpoint || 'https://api.deepseek.com/v1'
  form.api_key = ''
  form.model = config.model || 'deepseek-chat'
  form.parsing_mode = config.parsing_mode || 'generic'
  form.has_key = Boolean(config.has_key)
}

function editProvider(item) {
  try {
    form.id = item.id
    form.name = item.name
    form.endpoint = item.endpoint
    form.api_key = ''
    form.model = item.model
    form.parsing_mode = item.parsing_mode || 'generic'
    form.has_key = item.has_key
    testResult.value = null
    // 滚动到顶部，让用户能直接编辑
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    console.error('[editProvider] 异常', e)
    ElMessage.error('编辑失败：' + (e?.message || '未知错误'))
  }
}

function applyPreset(row) {
  form.id = row.id
  form.name = row.name
  form.endpoint = row.endpoint
  form.model = row.model
  form.api_key = ''
  form.has_key = providers.value.find((item) => item.id === row.id)?.has_key || false
}

function resetForm() {
  form.id = ''
  form.name = ''
  form.endpoint = 'https://api.deepseek.com/v1'
  form.api_key = ''
  form.model = 'deepseek-chat'
  form.parsing_mode = 'generic'
  form.has_key = false
  testResult.value = null
}

async function loadConfig() {
  const config = await getAiConfig()
  fillFromConfig(config)
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const config = await updateAiConfig({
      id: form.id || undefined,
      name: form.name,
      endpoint: form.endpoint,
      api_key: form.api_key || (form.has_key ? KEEP_KEY : ''),
      model: form.model,
      parsing_mode: form.parsing_mode
    })
    fillFromConfig(config)
    ElMessage.success('AI配置已保存并启用')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  if (!activeId.value) {
    ElMessage.warning('请先保存并启用一个配置')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const res = await testAiConnection()
    testResult.value = { success: true, latency: res.latency || '--' }
    ElMessage.success('连接成功')
  } catch (e) {
    testResult.value = { success: false, error: e?.response?.data?.detail || '连接失败' }
  } finally {
    testing.value = false
  }
}

async function activateProvider(item) {
  const config = await activateAiConfig(item.id)
  fillFromConfig(config)
  ElMessage.success(`已启用 ${item.name}`)
}

async function removeProvider(item) {
  try {
    await ElMessageBox.confirm(`确定删除「${item.name}」吗？此操作不可恢复。`, '删除配置', { type: 'warning' })
    const config = await deleteAiConfig(item.id)
    fillFromConfig(config)
    ElMessage.success('配置已删除')
  } catch (e) {
    if (e === 'cancel' || e?.message === 'cancel') return
    console.error('[removeProvider] 异常', e)
    ElMessage.error('删除失败：' + (e?.response?.data?.detail || e?.message || '未知错误'))
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.ai-hero {
  align-items: center;
}

.config-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
}

.config-main {
  display: grid;
  gap: 16px;
}

.config-panel {
  min-width: 0;
}

.panel-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.helper {
  margin-top: 4px;
}

.config-side {
  display: grid;
  align-content: start;
  gap: 16px;
}

.provider-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(78, 92, 130, 0.12);
  border-radius: 10px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.74);
  cursor: default;
}

.provider-item:hover {
  border-color: rgba(79, 124, 255, 0.32);
  box-shadow: 0 2px 12px rgba(31, 50, 88, 0.08);
}

.provider-item.active {
  border-color: rgba(79, 124, 255, 0.42);
  background: linear-gradient(135deg, rgba(79, 124, 255, 0.08), rgba(18, 182, 203, 0.06));
}

.provider-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.provider-info__head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.provider-model {
  font-size: 12px;
}

.provider-endpoint {
  color: #667085;
  font-size: 12px;
  word-break: break-all;
  margin-top: 2px;
  line-height: 1.5;
}

.provider-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px dashed rgba(78, 92, 130, 0.15);
  padding-top: 10px;
}

.provider-actions .el-button {
  flex: 1 1 auto;
  min-width: 78px;
}

.usage-list {
  display: grid;
  gap: 10px;
  color: #344054;
  font-size: 13px;
  line-height: 1.7;
}

.empty-mini {
  color: #98a2b3;
  font-size: 13px;
  padding: 12px 0;
}

@media (max-width: 1100px) {
  .config-layout {
    grid-template-columns: 1fr;
  }
}
</style>
