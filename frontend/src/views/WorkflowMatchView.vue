<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header page-hero workflow-hero">
      <div>
        <span class="eyebrow">Workflow Match Engine</span>
        <h2>工作流匹配</h2>
        <p class="text-muted">
          独立于平台搜人的AI匹配引擎，支持多种评估角色设定并可自由自定义，
          对候选人简历与JD进行专业化的自动打分分析。
        </p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" plain @click="openRoleEditor(null)">
          <el-icon><Plus /></el-icon>
          新建角色
        </el-button>
        <el-button type="primary" @click="handleMatchAll" :loading="matching" :disabled="!selectedPositionId">
          <el-icon><MagicStick /></el-icon>
          全部匹配
        </el-button>
      </div>
    </div>

    <!-- 配置区域：角色选择 + 任务配置 -->
    <div class="config-strip">
      <!-- 角色设定卡片 -->
      <el-card class="glass-card role-config-card">
        <template #header>
          <div class="card-header-line">
            <div>
              <strong><el-icon><UserFilled /></el-icon>评估角色设定</strong>
              <div class="text-muted">选择或创建评估视角，不同角色关注维度不同。内置角色不可修改，自定义角色支持完全定制。</div>
            </div>
            <el-tag :type="currentResolved ? 'success' : 'info'" effect="plain">
              {{ currentResolved?.name || '未选择' }}
            </el-tag>
          </div>
        </template>

        <!-- 内置角色 -->
        <div class="section-label">内置预设角色</div>
        <div class="role-selector">
          <div
            v-for="(role, key) in builtinRoles"
            :key="'b_' + key"
            class="role-option"
            :class="{ 'role-option--active': selectedRoleId === 'builtin_' + key }"
            @click="selectBuiltin(key)"
          >
            <div class="role-option__icon"><component :is="roleIcons[key]" /></div>
            <div class="role-option__info">
              <strong>{{ role.name }}</strong>
              <span class="text-muted role-option__desc">{{ role.description }}</span>
              <span class="role-option__dims">{{ role.dimensionsCount }} 个维度 · 只读</span>
            </div>
            <el-tag v-if="selectedRoleId === 'builtin_' + key" size="small" type="success" effect="dark" round>已选</el-tag>
          </div>
        </div>

        <!-- 自定义角色 -->
        <template v-if="customRoles.length">
          <el-divider content-position="left">我的自定义角色</el-divider>
          <div class="section-label" style="margin-top: 0;">
            自定义角色 ({{ customRoles.length }} 个)
            <el-button size="small" text type="primary" style="margin-left: 8px;" @click="openRoleEditor(null)">
              + 新建
            </el-button>
          </div>
          <div class="role-selector">
            <div
              v-for="crole in customRoles"
              :key="'c_' + crole.id"
              class="role-option role-option--custom"
              :class="{ 'role-option--active': selectedRoleId === String(crole.id) }"
              @click="selectCustom(crole.id)"
            >
              <div class="role-option__icon" style="background: linear-gradient(135deg, rgba(230,162,60,0.15), rgba(245,108,108,0.08)); color: #e6a23c;">
                <EditPen />
              </div>
              <div class="role-option__info">
                <strong>{{ crole.name }}</strong>
                <span class="text-muted role-option__desc">{{ crole.description || '无描述' }}</span>
                <span class="role-option__dims">{{ crole.dimensions_count }} 个维度</span>
              </div>
              <div class="role-option__actions">
                <el-tag v-if="selectedRoleId === String(crole.id)" size="small" type="warning" effect="dark" round>已选</el-tag>
                <el-button size="small" text type="primary" @click.stop="openRoleEditor(crole)">编辑</el-button>
                <el-button size="small" text type="danger" @click.stop="handleDeleteCustomRole(crole)">删除</el-button>
              </div>
            </div>
          </div>
        </template>

        <el-empty v-if="!customRoles.length && !loadingRoles" description="暂无自定义角色，点击「新建角色」创建专属评估人设" :image-size="80" />

        <!-- 维度预览 -->
        <el-divider />
        <div v-if="currentResolvedDetail" class="dimension-preview">
          <div class="section-subtitle">
            {{ currentResolvedDetail.is_builtin ? '[内置]' : '[自定义]' }}
            {{ currentResolvedDetail.name }} - 评分维度
          </div>
          <div class="dimension-list">
            <div v-for="(dim, idx) in currentResolvedDetail.eval_dimensions" :key="idx" class="dimension-item">
              <span class="dim-index">{{ idx + 1 }}</span>
              <div class="dim-info">
                <strong>{{ dim.name }}</strong>
                <span class="text-muted dim-desc">{{ dim.desc }}</span>
              </div>
              <el-tag size="small" effect="plain">0-{{ dim.max_score }}分</el-tag>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 任务配置卡片 -->
      <el-card class="glass-card task-config-card">
        <template #header>
          <div class="card-header-line">
            <strong><el-icon><Document /></el-icon>匹配任务配置</strong>
          </div>
        </template>
        <el-form label-width="90px">
          <el-form-item label="目标职位">
            <el-select v-model="selectedPositionId" placeholder="选择要匹配的职位" filterable @change="loadCandidates">
              <el-option v-for="item in positions" :key="item.id" :label="item.title" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="最低分过滤">
            <el-input-number v-model="minScoreFilter" :min="0" :max="100" :step="5" />
            <div class="form-tip">低于此分数的候选人将不显示</div>
          </el-form-item>
          <el-form-item label="候选人数">
            <div class="candidate-count-badge">{{ candidates.length }} 人</div>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 结果区域 -->
    <div v-if="matchResults.length || matching" class="results-section">
      <el-card class="glass-card results-card">
        <template #header>
          <div class="card-header-line">
            <div>
              <strong>匹配结果</strong>
              <div v-if="batchResult" class="text-muted">
                扫描 {{ batchResult.total_count }} 人，命中 {{ batchResult.matched_count }} 人
                ，均分 <strong>{{ batchResult.avg_score }}</strong>
                · 角色：<em>{{ batchResult.role_name }}</em>
              </div>
            </div>
            <div class="hero-actions" v-if="matchResults.length">
              <el-button size="small" text type="info" @click="clearResults">清空</el-button>
            </div>
          </div>
        </template>

        <!-- 统计概览 -->
        <div v-if="matchResults.length" class="stats-row">
          <div class="stat-chip stat-chip--excellent"><span class="stat-label">优秀 (≥80)</span><strong>{{ excellentCount }}</strong></div>
          <div class="stat-chip stat-chip--good"><span class="stat-label">良好 (60-79)</span><strong>{{ goodCount }}</strong></div>
          <div class="stat-chip stat-chip--fair"><span class="stat-label">一般 (40-59)</span><strong>{{ fairCount }}</strong></div>
          <div class="stat-chip stat-chip--poor"><span class="stat-label">待提升 (&lt;40)</span><strong>{{ poorCount }}</strong></div>
        </div>

        <el-empty v-if="!matchResults.length && !matching" description="请执行匹配操作" />

        <div v-if="matching" class="matching-loader">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <p>正在使用「{{ currentResolved?.name || '资深招聘专家' }}」进行智能匹配...</p>
        </div>

        <el-table v-if="matchResults.length" :data="matchResults" stripe row-key="candidate_id" default-expand-all>
          <el-table-column prop="candidate_name" label="候选人" min-width="140" fixed>
            <template #default="{ row }"><strong>{{ row.candidate_name }}</strong></template>
          </el-table-column>
          <el-table-column label="总分" width="100" sortable :sort-method="(a,b)=>a.score-b.score" fixed>
            <template #default="{ row }">
              <el-tag :type="scoreTagType(row.score)" size="large" effect="dark" round>{{ row.score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="hasDimensionScores" label="维度得分" min-width="280">
            <template #default="{ row }">
              <div v-if="row.dimension_scores" class="dim-score-bars">
                <div v-for="(val, name) in row.dimension_scores" :key="name" class="dim-bar-row">
                  <span class="dim-bar-name">{{ name }}</span>
                  <el-progress :percentage="val" :stroke-width="8" :color="getProgressColor(val)" :show-text="true" :format="() => val + '分'" />
                </div>
              </div>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }"><el-button size="small" @click="showAnalysisDetail(row)">查看详情</el-button></template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-empty v-else description="请先选择职位和评估角色，然后点击「全部匹配」开始分析" :image-size="120" />

    <!-- ===== 角色编辑器对话框 ===== -->
    <el-dialog
      v-model="editorVisible"
      :title="editingRole ? '编辑自定义角色' : '新建自定义角色'"
      width="720px"
      top="5vh"
      destroy-on-close
      class="role-editor-dialog"
      @opened="onEditorOpened"
    >
      <el-form ref="editorFormRef" :model="editorForm" :rules="editorRules" label-width="90px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="editorForm.name" placeholder="如：Java高级架构师面试官" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input v-model="editorForm.description" type="textarea" :rows="2" placeholder="简短描述该角色的定位和适用场景" maxlength="300" show-word-limit />
        </el-form-item>

        <el-form-item label="AI人设/提示词" prop="system_prompt" required>
          <el-input
            v-model="editorForm.system_prompt"
            type="textarea"
            :rows="5"
            placeholder="定义AI扮演的角色、评估风格和侧重点&#10;&#10;例如：你是一位拥有20年经验的CTO级别技术负责人..."
            maxlength="5000"
            show-word-limit
          />
          <div class="form-tip">这段文字会作为系统提示词发送给AI，决定它的回答风格和分析深度。</div>
        </el-form-item>

        <el-form-item label="评分维度" required>
          <div class="dims-editor">
            <div v-for="(dim, idx) in editorForm.dimensions" :key="idx" class="dim-edit-row">
              <el-input v-model="dim.name" placeholder="维度名称" style="width: 160px;" />
              <el-input-number v-model="dim.max_score" :min="1" :max="100" size="small" controls-position="right" style="width: 110px;" />
              <span class="dim-max-label">分</span>
              <el-input v-model="dim.desc" placeholder="说明" style="flex:1; min-width:0;" />
              <el-button size="small" type="danger" text circle :disabled="editorForm.dimensions.length <= 1" @click="removeDimension(idx)">
                <el-icon><Minus /></el-icon>
              </el-button>
              <div v-if="editorForm.dimensions.length > 1" class="dim-drag-handle">⠿</div>
            </div>
            <div class="dims-total">
              <span>共 {{ editorForm.dimensions.length }} 个维度</span>
              <span class="dims-max-sum">
                满分合计: <strong :style="{ color: dimsTotalMax > 120 ? '#f56c6c' : dimsTotalMax > 100 ? '#e6a23c' : '#67c23a' }">{{ dimsTotalMax }}</strong>
                <span class="text-muted" style="font-size:12px; margin-left:4px;">（建议100左右）</span>
              </span>
            </div>

            <el-button size="small" @click="addDimension" style="margin-top: 8px;">
              <el-icon><Plus /></el-icon> 添加维度
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingRole" @click="saveRole">{{ editingRole ? '保存修改' : '创建角色' }}</el-button>
      </template>
    </el-dialog>

    <!-- 分析详情弹窗 -->
    <el-dialog v-model="analysisDialog.visible" :title="`「${analysisDialog.data?.candidate_name}」匹配报告`" width="720px" top="5vh">
      <div v-if="analysisDialog.data" class="analysis-body">
        <div class="analysis-header">
          <div class="analysis-score-big">
            <span class="score-num">{{ analysisDialog.data.score }}</span>
            <span class="score-label">综合得分</span>
          </div>
          <div v-if="analysisDialog.data.dimension_scores" class="analysis-dims-mini">
            <div v-for="(val, name) in analysisDialog.data.dimension_scores" :key="name" class="mini-dim">
              <span class="mini-dim-name">{{ name }}</span>
              <span class="mini-dim-val" :class="'val--' + getScoreLevel(val)">{{ val }}</span>
            </div>
          </div>
        </div>
        <el-divider />
        <div class="analysis-content markdown-body" v-html="renderMarkdown(analysisDialog.data.analysis)"></div>
      </div>
      <template #footer><el-button @click="analysisDialog.visible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  EditPen,
  Loading,
  MagicStick,
  Minus,
  Plus,
  Select,
  UserFilled,
} from '@element-plus/icons-vue'
import { getPositions } from '../api/positions'
import { getCandidates } from '../api/candidates'
import {
  getWorkflowRoles,
  getWorkflowRoleDetail,
  createCustomRole,
  updateCustomRole,
  deleteCustomRole as apiDeleteRole,
  workflowMatchAll,
} from '../api/workflow'
import { renderSafeMarkdown } from '../utils/safeMarkdown'

// ==================== State ====================
const loading = ref(false)
const loadingRoles = ref(false)
const matching = ref(false)
const savingRole = ref(false)

const positions = ref([])
const candidates = ref([])
const selectedPositionId = ref(null)
const minScoreFilter = ref(0)
const matchResults = ref([])
const batchResult = ref(null)

// 角色
const builtinRoles = ref({})
const customRoles = ref([])
const selectedRoleId = ref('builtin_recruiter')
const currentResolved = ref(null)
const currentResolvedDetail = ref(null)

const roleIcons = { recruiter: UserFilled, tech_interviewer: UserFilled, hr_bp: UserFilled, hiring_manager: UserFilled }

// 角色编辑器
const editorVisible = ref(false)
const editingRole = ref(null)  // null=新建, object=编辑
const editorFormRef = ref()
const editorForm = reactive({
  name: '',
  description: '',
  system_prompt: '',
  dimensions: [{ name: '综合匹配度', max_score: 100, desc: '综合评估候选人与岗位的匹配程度' }],
})
const editorRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  system_prompt: [{ required: true, message: '请输入AI人设提示词', trigger: 'blur' }],
}

// 分析弹窗
const analysisDialog = reactive({ visible: false, data: null })

// ==================== Computed ====================
const hasDimensionScores = computed(() => matchResults.value.some(r => r.dimension_scores && Object.keys(r.dimension_scores).length > 0))
const excellentCount = computed(() => matchResults.value.filter(r => r.score >= 80).length)
const goodCount = computed(() => matchResults.value.filter(r => r.score >= 60 && r.score < 80).length)
const fairCount = computed(() => matchResults.value.filter(r => r.score >= 40 && r.score < 60).length)
const poorCount = computed(() => matchResults.value.filter(r => r.score < 40).length)

const dimsTotalMax = computed(() => editorForm.dimensions.reduce((sum, d) => sum + (d.max_score || 0), 0))

function renderMarkdown(text) {
  return renderSafeMarkdown(text)
}

// ==================== Methods ====================
function scoreTagType(s) { if (s >= 80) return 'success'; if (s >= 60) return 'primary'; if (s >= 40) return 'warning'; return 'danger' }
function getScoreLevel(s) { if (s >= 80) return 'excellent'; if (s >= 60) return 'good'; if (s >= 40) return 'fair'; return 'poor' }
function getProgressColor(p) { if (p >= 80) return '#67c23a'; if (p >= 60) return '#409eff'; if (p >= 40) return '#e6a23c'; return '#f56c6c' }

// ---- 角色加载 ----
async function loadRoles() {
  loadingRoles.value = true
  try {
    const res = await getWorkflowRoles()
    // 内置
    builtinRoles.value = {}
    for (const r of res.roles) {
      if (r.is_builtin) builtinRoles.value[r.role_key] = r
    }
    // 自定义
    customRoles.value = res.roles.filter(r => !r.is_builtin)
  } catch (e) { console.error('加载角色失败', e) } finally { loadingRoles.value = false }
}

async function selectBuiltin(key) {
  selectedRoleId.value = 'builtin_' + key
  try { currentResolvedDetail.value = await getWorkflowRoleDetail('builtin_' + key); currentResolved.value = currentResolvedDetail.value }
  catch { currentResolvedDetail.value = null; currentResolved.value = null }
}

async function selectCustom(id) {
  selectedRoleId.value = String(id)
  try { currentResolvedDetail.value = await getWorkflowRoleDetail(String(id)); currentResolved.value = currentResolvedDetail.value }
  catch { currentResolvedDetail.value = null; currentResolved.value = null }
}

// 初始化选中角色的详情
async function initSelectedDetail() {
  if (!selectedRoleId.value) return
  try { currentResolvedDetail.value = await getWorkflowRoleDetail(selectedRoleId.value); currentResolved.value = currentResolvedDetail.value }
  catch { currentResolvedDetail.value = null }
}

// ---- 角色CRUD ----
function openRoleEditor(roleObj) {
  editingRole.value = roleObj
  if (roleObj) {
    editorForm.name = roleObj.name || ''
    editorForm.description = ''
    editorForm.system_prompt = ''
    editorForm.dimensions = [{ name: '综合匹配度', max_score: 100, desc: '' }]
    // 异步加载详情
    getWorkflowRoleDetail(String(roleObj.id)).then(detail => {
      editorForm.name = detail.name || editorForm.name
      editorForm.description = detail.description || ''
      editorForm.system_prompt = detail.system_prompt || editorForm.system_prompt
      if (detail.eval_dimensions?.length) {
        editorForm.dimensions = detail.eval_dimensions.map(d => ({ ...d }))
      }
    }).catch(() => {})
  } else {
    editorForm.name = ''
    editorForm.description = ''
    editorForm.system_prompt = ''
    editorForm.dimensions = [
      { name: '综合匹配度', max_score: 100, desc: '综合评估' },
      { name: '技能匹配', max_score: 30, desc: '技能与岗位要求匹配程度' },
      { name: '经验相关度', max_score: 25, desc: '过往经历与目标岗位的相关性' },
      { name: '潜力评估', max_score: 20, desc: '学习能力和成长空间' },
      { name: '文化契合', max_score: 25, desc: '价值观和软性素质' },
    ]
  }
  editorVisible.value = true
}

function onEditorOpened() { /* form reset handled by openRoleEditor */ }

function addDimension() {
  editorForm.dimensions.push({ name: '', max_score: 20, desc: '' })
}

function removeDimension(idx) {
  if (editorForm.dimensions.length > 1) editorForm.dimensions.splice(idx, 1)
}

function validateDimensions() {
  const dims = editorForm.dimensions
  for (let i = 0; i < dims.length; i++) {
    if (!dims[i].name?.trim()) { ElMessage.warning(`第 ${i+1} 个维度名称不能为空`); return false }
    if (!dims[i].max_score || dims[i].max_score < 1) { ElMessage.warning(`第 ${i+1} 个维度的满分必须大于0`); return false }
  }
  return true
}

async function saveRole() {
  if (!validateDimensions()) return
  try {
    await editorFormRef.value.validate()
  } catch { return }

  savingRole.value = true
  try {
    const payload = {
      name: editorForm.name.trim(),
      description: editorForm.description?.trim() || undefined,
      system_prompt: editorForm.system_prompt.trim(),
      eval_dimensions: editorForm.dimensions.map(d => ({
        name: d.name.trim(),
        max_score: Number(d.max_score),
        desc: d.desc?.trim() || '',
      })),
    }

    if (editingRole.value) {
      await updateCustomRole(editingRole.value.id, payload)
      ElMessage.success('角色已更新')
    } else {
      await createCustomRole(payload)
      ElMessage.success('角色已创建')
    }

    editorVisible.value = false
    await loadRoles()
    // 如果当前选中的是被编辑的角色，刷新详情
    if (editingRole.value && selectedRoleId.value === String(editingRole.value.id)) {
      await initSelectedDetail()
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingRole.value = false
  }
}

async function handleDeleteCustomRole(role) {
  try {
    await ElMessageBox.confirm(
      `确定删除自定义角色「${role.name}」吗？此操作不可恢复。`,
      '删除角色',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await apiDeleteRole(role.id)
    ElMessage.success('角色已删除')

    if (selectedRoleId.value === String(role.id)) {
      selectedRoleId.value = 'builtin_recruiter'
      await initSelectedDetail()
    }

    await loadRoles()
  } catch (e) { if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败') }
}

// ---- 匹配 ----
async function loadPositions() {
  try {
    positions.value = await getPositions({ status: '开放' })
    if (positions.value.length && !selectedPositionId.value) selectedPositionId.value = positions.value[0].id
  } catch (e) { console.error(e) }
}
async function loadCandidates() {
  if (!selectedPositionId.value) return
  try {
    const list = await getCandidates({ position_id: selectedPositionId.value })
    candidates.value = list.items || list || []
  } catch (e) { candidates.value = [] }
}

async function handleMatchAll() {
  if (!selectedPositionId.value) { ElMessage.warning('请先选择职位'); return }

  matching.value = true; matchResults.value = []; batchResult.value = null

  try {
    // 构建role_config
    let role_config = {}
    if (selectedRoleId.value.startsWith('builtin_')) {
      role_config.builtin_role_type = selectedRoleId.value.replace('builtin_', '')
    } else {
      role_config.custom_role_id = parseInt(selectedRoleId.value, 10)
    }

    const res = await workflowMatchAll({
      position_id: selectedPositionId.value,
      role_config,
      min_score: minScoreFilter.value,
    })

    batchResult.value = res
    matchResults.value = res.results
    ElMessage.success(`完成！${res.matched_count} 人通过筛选`)
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '匹配失败') }
  finally { matching.value = false }
}

function showAnalysisDetail(row) { analysisDialog.data = row; analysisDialog.visible = true }
function clearResults() { matchResults.value = []; batchResult.value = null }

// ==================== Lifecycle ====================
onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadPositions(), loadRoles()])
    await initSelectedDetail()
    if (selectedPositionId.value) await loadCandidates()
  } finally { loading.value = false }
})
</script>

<style scoped>
.workflow-hero { align-items: center; }

.config-strip { display: grid; grid-template-columns: 1.3fr 0.7fr; gap: 16px; margin-bottom: 20px; }

.section-label { font-weight: 700; font-size: 13px; color: #667085; margin-bottom: 10px; display: flex; align-items: center; }

/* 角色选择器 */
.role-selector { display: flex; flex-direction: column; gap: 10px; }

.role-option {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border: 2px solid rgba(78,92,130,.12);
  border-radius: 10px; cursor: pointer; transition: all .2s ease;
  background: rgba(255,255,255,.6);
}
.role-option:hover { border-color: rgba(79,124,255,.35); background: rgba(255,255,255,.85); }
.role-option--active { border-color: #2f63ff; background: rgba(79,124,255,.06); box-shadow: 0 2px 12px rgba(47,99,255,.12); }
.role-option--custom:hover { border-color: rgba(230,162,60,.35); }
.role-option--custom.role-option--active { border-color: #e6a23c; background: rgba(230,162,60,.06); box-shadow: 0 2px 12px rgba(230,162,60,.12); }

.role-option__icon {
  width: 40px; height: 40px; border-radius: 10px;
  background: linear-gradient(135deg, rgba(79,124,255,.15), rgba(79,124,255,.05));
  color: #2f63ff; display: inline-flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.role-option__info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.role-option__desc { font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.role-option__dims { font-size: 11px; color: #365ec8; }
.role-option__actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }

/* 维度预览 */
.dimension-preview { padding: 8px 0 0; }
.section-subtitle { font-weight: 700; font-size: 13px; color: #162033; margin-bottom: 10px; }
.dimension-list { display: flex; flex-direction: column; gap: 8px; }
.dimension-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 8px; background: rgba(246,247,250,.7);
}
.dim-index {
  width: 22px; height: 22px; border-radius: 6px;
  background: rgba(79,124,255,.12); color: #2f63ff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.dim-info { flex: 1; display: flex; flex-direction: column; gap: 1px; }
.dim-desc { font-size: 11px; }

/* 表单辅助 */
.form-tip { font-size: 12px; color: #909399; line-height: 1.5; }
.candidate-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 6px 14px; border-radius: 16px; background: rgba(79,124,255,.08);
  color: #2f63ff; font-weight: 600; font-size: 13px;
}

/* 结果区域 */
.results-section { display: flex; flex-direction: column; gap: 16px; }
.stats-row {
  display: flex; gap: 12px; flex-wrap: wrap; padding: 16px;
  border-radius: 10px; background: rgba(245,247,252,.85);
}
.stat-chip { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 8px; font-size: 13px; }
.stat-chip strong { font-size: 18px; }
.stat-chip--excellent { background: rgba(103,194,58,.1); }
.stat-chip--good { background: rgba(64,158,255,.1); }
.stat-chip--fair { background: rgba(230,162,60,.1); }
.stat-chip--poor { background: rgba(245,108,108,.1); }

/* 维度进度条 */
.dim-score-bars { display: flex; flex-direction: column; gap: 6px; }
.dim-bar-row { display: flex; align-items: center; gap: 8px; }
.dim-bar-name { width: 80px; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }

/* 匹配动画 */
.matching-loader { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 48px 0; color: #667085; }
.matching-loader p { font-size: 14px; }

/* ===== 角色编辑器样式 ===== */
.dims-editor { width: 100%; }
.dim-edit-row {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border: 1px solid rgba(78,92,130,.1); border-radius: 8px;
  background: rgba(248,249,252,.6); transition: border-color .2s;
}
.dim-edit-row:hover { border-color: rgba(79,124,255,.3); }
.dim-edit-row:focus-within { border-color: #409eff; }
.dim-max-label { font-size: 13px; color: #667085; white-space: nowrap; }
.dim-drag-handle {
  cursor: grab; color: #c0c4cc; font-size: 16px; user-select: none;
  padding: 0 2px; line-height: 1;
}
.dims-total {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; border-radius: 6px; background: rgba(246,247,250,.8);
  font-size: 12px; color: #667085; margin-top: 8px;
}
.dims-max-sum { font-size: 13px; }

/* 分析弹窗 */
.analysis-header { display: flex; align-items: center; gap: 32px; padding: 16px 0; }
.analysis-score-big { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.score-num {
  font-size: 48px; font-weight: 800; line-height: 1;
  background: linear-gradient(135deg, #2f63ff, #00d4aa); -webkit-background-clip: text;
  -webkit-text-fill-color: transparent; background-clip: text;
}
.score-label { font-size: 12px; color: #909399; }
.analysis-dims-mini { display: flex; flex-wrap: wrap; gap: 12px; flex: 1; }
.mini-dim { display: flex; flex-direction: column; gap: 2px; padding: 8px 12px; border-radius: 8px; background: rgba(246,247,250,.9); min-width: 100px; }
.mini-dim-name { font-size: 11px; color: #667085; }
.mini-dim-val { font-size: 20px; font-weight: 700; }
.mini-dim-val.val--excellent{color:#67c23a} .mini-dim-val.val--good{color:#409eff}
.mini-dim-val.val--fair{color:#e6a23c} .mini-dim-val.val--poor{color:#f56c6c}
.analysis-content { line-height: 1.8; color: #344054; }
.analysis-content :deep(h3){font-size:17px;margin-top:16px;margin-bottom:8px;color:#162033;}
.analysis-content :deep(h4){font-size:15px;margin-top:12px;margin-bottom:6px;color:#344054;}
.analysis-content :deep(strong){color:#162033;}
.analysis-content :deep(li){margin-left:20px;margin-bottom:4px;}

@media (max-width: 1100px) { .config-strip { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .role-option { flex-wrap: wrap; } }
</style>
