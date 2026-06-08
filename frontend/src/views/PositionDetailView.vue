<template>
  <div class="page-container">
    <el-alert
      v-if="pageError"
      type="error"
      :title="`加载出错：${pageError}`"
      show-icon
      :closable="false"
      style="margin-bottom: 16px;"
    >
      <template #default>
        <el-button size="small" type="primary" @click="reload">刷新页面</el-button>
      </template>
    </el-alert>
    <div v-if="pageError" class="page-error-placeholder">
      请尝试刷新页面或联系管理员。
    </div>
    <div v-else class="page-header position-hero">
      <div>
        <span class="eyebrow">Position Workspace</span>
        <h2>{{ position.title }}</h2>
        <p class="text-muted">{{ position.department }} · {{ position.location }} · {{ position.salary_range || '薪资面议' }}</p>
      </div>
      <div class="hero-actions">
        <el-button @click="$router.push(`/positions/${position.id}/edit`)">
          <el-icon><Edit /></el-icon>
          编辑职位
        </el-button>
        <el-button type="danger" plain @click="handleDelete">
          <el-icon><Delete /></el-icon>
          删除职位
        </el-button>
      </div>
    </div>

    <el-card class="glass-card jd-card">
      <template #header><strong>岗位JD</strong></template>
      <div class="rich-text">{{ position.job_description }}</div>
      <div v-if="position.requirements" class="requirement-block">
        <strong>任职要求：</strong>
        <div class="rich-text">{{ position.requirements }}</div>
      </div>
    </el-card>

    <el-card class="glass-card upload-card">
      <template #header>
        <div class="flex-between">
          <strong>上传简历 & 角色匹配</strong>
          <span class="text-muted">支持 PDF、Word 格式，可批量上传</span>
        </div>
      </template>
      <div class="upload-workspace">
        <el-upload
          ref="uploadRef"
          drag
          multiple
          :auto-upload="false"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          accept=".pdf,.doc,.docx"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将简历文件拖拽到此区域，或 <em>点击选择文件</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              已选择 <strong>{{ uploadFilesCount }}</strong> 个文件
              <span v-if="uploadFilesCount > 0" class="upload-file-names">
                （{{ uploadFileNames }}）
              </span>
            </div>
          </template>
        </el-upload>

        <!-- 评估角色选择（纵向排列，避免与上传区抢宽度） -->
        <div class="role-pick-block">
          <div class="role-pick-head">
            <div class="role-pick-label">
              <el-icon><UserFilled /></el-icon>
              评估角色
            </div>
            <el-button size="small" plain type="primary" class="manage-role-btn" @click="$router.push('/workflow-match')">
              <el-icon><Setting /></el-icon>
              管理自定义角色
            </el-button>
          </div>
          <el-select v-model="selectedRoleId" placeholder="选择评估角色（用于一键打分）" class="role-pick-select">
            <el-option-group label="内置预设">
              <el-option
                v-for="(r, key) in builtinRoles"
                :key="'b_' + key"
                :label="r.name"
                :value="'builtin_' + key"
              >
                <span style="float: left;">{{ r.name }}</span>
                <span style="float: right; font-size: 11px; color: #909399;">{{ r.description }}</span>
              </el-option>
            </el-option-group>
            <el-option-group v-if="customRoles.length" label="我的自定义角色">
              <el-option
                v-for="r in customRoles"
                :key="'c_' + r.id"
                :label="r.name"
                :value="String(r.id)"
              >
                <span style="float: left;">{{ r.name }}</span>
                <span style="float: right; font-size: 11px; color: #909399;">{{ r.description || '自定义角色' }}</span>
              </el-option>
            </el-option-group>
          </el-select>
        </div>

        <div class="upload-actions">
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="uploadFilesCount === 0"
            @click="handleUpload"
          >
            <el-icon><Upload /></el-icon>
            上传并解析简历
          </el-button>
          <el-button
            v-if="candidates.length > 0"
            type="success"
            :loading="matching"
            :disabled="!selectedRoleId"
            @click="handleBatchMatch"
          >
            <el-icon><MagicStick /></el-icon>
            用「{{ currentRoleName }}」一键打分
          </el-button>
        </div>
      </div>

      <div v-if="uploadProgress.show" class="progress-block">
        <el-progress
          :percentage="uploadProgress.percent"
          :status="uploadProgress.status"
          :text-inside="true"
          :stroke-width="20"
        />
        <p class="text-muted">{{ uploadProgress.text }}</p>
      </div>

      <div v-if="matchSummary.show" class="match-summary-block">
        <el-alert
          :title="`批量打分完成 · 角色：${currentRoleName}`"
          :type="matchSummary.failed > 0 ? 'warning' : 'success'"
          :closable="true"
          show-icon
          @close="matchSummary.show = false"
        >
          <template #default>
            扫描 <strong>{{ matchSummary.total }}</strong> 人，
            成功打分 <strong>{{ matchSummary.success }}</strong> 人，
            平均分 <strong>{{ matchSummary.avg }}</strong> 分
            <span v-if="matchSummary.failed > 0" style="color: #f56c6c;">
              ，失败 {{ matchSummary.failed }} 人
            </span>
            <div v-if="matchSummary.failed > 0 && matchSummary.failedReasons?.length" class="failure-reasons">
              <div class="failure-reasons__title">失败原因（前 {{ Math.min(matchSummary.failedReasons.length, 5) }} 条）：</div>
              <ul>
                <li v-for="(r, i) in matchSummary.failedReasons.slice(0, 5)" :key="i">{{ r }}</li>
              </ul>
            </div>
          </template>
        </el-alert>
      </div>
    </el-card>

    <el-card class="glass-card candidate-console">
      <template #header>
        <div class="candidate-toolbar">
          <div>
            <strong>候选人排名</strong>
            <span class="text-muted">共 {{ candidates.length }} 人，按匹配度从高到低</span>
          </div>
          <div class="candidate-toolbar__actions">
            <el-checkbox
              :model-value="isAllSelected"
              :indeterminate="isIndeterminate"
              :disabled="!candidates.length"
              @change="toggleSelectAll"
            >
              全选
            </el-checkbox>
            <el-button type="danger" plain :disabled="!selectedIds.length" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon>
              批量删除<span v-if="selectedIds.length">（{{ selectedIds.length }}）</span>
            </el-button>
            <el-tag type="primary" effect="plain">评分与标签已前置展示</el-tag>
          </div>
        </div>
      </template>

      <el-empty v-if="!candidates.length" description="暂无候选人，上传简历后会出现在这里" />

      <div v-else v-loading="candidateLoading" class="candidate-grid">
        <article v-for="row in candidates" :key="row.id" :ref="(el) => setCandidateRef(row.id, el)" :class="['candidate-card', { 'candidate-card--focused': reportDialog.data?.id === row.id }]">
          <div class="candidate-card__top">
            <div>
              <div class="candidate-name">{{ row.name }}</div>
              <div class="candidate-meta">
                <span>{{ row.current_position || '暂无职位' }}</span>
                <span>{{ row.current_company || '暂无公司' }}</span>
              </div>
            </div>
            <el-checkbox :model-value="selectedIds.includes(row.id)" @change="toggleSelect(row.id, $event)" />
          </div>

          <div class="candidate-status-strip">
            <div v-if="row.match_score != null && row.match_score > 0" class="score-pill" :style="{ '--score-color': getScoreColor(row.match_score) }">
              <strong>{{ row.match_score }}</strong>
              <span>{{ getScoreLevel(row.match_score) }}</span>
            </div>
            <el-tag v-else-if="row.match_score === 0" size="small" type="warning" effect="plain">
              <el-icon><Warning /></el-icon>
              匹配失败
            </el-tag>
            <el-tag v-else size="small" type="info" effect="plain">未匹配</el-tag>
            <el-tag :type="STATUS_COLORS[row.status]" size="small">{{ row.status }}</el-tag>
            <el-tag
              v-if="row.match_score != null && row.match_score > 0 && row.has_relevant_experience === true"
              size="small"
              type="success"
              effect="dark"
              class="relevant-tag"
            >
              <el-icon><Star /></el-icon>
              有相关经验
            </el-tag>
            <el-tag
              v-else-if="row.match_score != null && row.match_score > 0 && row.has_relevant_experience === false"
              size="small"
              type="info"
              effect="plain"
              class="relevant-tag"
            >
              经验不相关
            </el-tag>
          </div>

          <div class="candidate-info-grid">
            <div class="candidate-field">
              <span class="field-label">电话</span>
              <div class="inline-copy">
                <span class="copy-text">{{ row.phone || '-' }}</span>
                <el-tooltip v-if="row.phone" content="复制电话" placement="top">
                  <el-button text circle size="small" class="copy-icon-btn" @click="copyText(row.phone, '电话')">
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>

            <div class="candidate-field">
              <span class="field-label">邮箱</span>
              <div class="inline-copy">
                <span class="copy-text">{{ row.email || '-' }}</span>
                <el-tooltip v-if="row.email" content="复制邮箱" placement="top">
                  <el-button text circle size="small" class="copy-icon-btn" @click="copyText(row.email, '邮箱')">
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </div>

          <div class="candidate-field">
            <span class="field-label">标签</span>
            <div v-if="row.skills?.length" class="tag-cloud">
              <el-tag v-for="skill in row.skills" :key="skill.id || skill.skill_name" size="small" effect="plain">
                {{ skill.skill_name }}<span v-if="skill.proficiency"> · {{ skill.proficiency }}</span>
              </el-tag>
            </div>
            <span v-else class="text-muted">待解析</span>
          </div>

          <div class="candidate-actions">
            <el-button size="small" @click="$router.push(`/candidates/${row.id}`)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button v-if="row.match_score != null && row.match_score > 0" size="small" type="primary" plain @click="openReportDialog(row)">
              <el-icon><Document /></el-icon>
              报告
            </el-button>
            <el-button v-if="row.match_score == null || row.match_score === 0" size="small" type="primary" :loading="row._matching" @click="handleSingleMatch(row)">
              <el-icon><MagicStick /></el-icon>
              {{ row.match_score === 0 ? '重试匹配' : '匹配' }}
            </el-button>
            <el-dropdown @command="(cmd) => handleStatusChange(row, cmd)">
              <el-button size="small">
                <el-icon><RefreshRight /></el-icon>
                状态
                <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="待联系">待联系</el-dropdown-item>
                  <el-dropdown-item command="已联系">已联系</el-dropdown-item>
                  <el-dropdown-item command="面试中">面试中</el-dropdown-item>
                  <el-dropdown-item command="已通过">已通过</el-dropdown-item>
                  <el-dropdown-item command="已淘汰">已淘汰</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button size="small" type="danger" plain @click="handleDeleteCandidate(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </article>
      </div>
    </el-card>

    <!-- 候选人匹配报告浮层（位置跟随候选人卡片，绝不跑偏） -->
    <Teleport to="body">
      <Transition name="report-fade">
        <div v-if="reportDialog.visible" class="report-overlay" @click.self="closeReport">
          <div
            class="report-floating"
            :style="reportDialog.position"
            @click.stop
          >
            <div class="report-floating__header">
              <div class="report-floating__title">
                <el-icon><Document /></el-icon>
                <strong>「{{ reportDialog.data?.name }}」匹配报告</strong>
              </div>
              <button class="report-floating__close" @click="closeReport" aria-label="关闭">
                <el-icon><Close /></el-icon>
              </button>
            </div>
            <div v-if="reportDialog.data" class="analysis-body">
              <div class="analysis-header">
                <div class="analysis-score-big">
                  <span class="score-num">{{ reportDialog.data.match_score ?? '—' }}</span>
                  <span class="score-label">综合得分</span>
                </div>
                <div v-if="reportDialog.dim_scores" class="analysis-dims-mini">
                  <div v-for="(val, name) in reportDialog.dim_scores" :key="name" class="mini-dim">
                    <span class="mini-dim-name">{{ name }}</span>
                    <span class="mini-dim-val" :class="'val--' + getScoreLevel(val)">{{ val }}</span>
                  </div>
                </div>
              </div>
              <el-divider />
              <div class="analysis-content markdown-body" v-html="renderMarkdown(reportDialog.analysis)"></div>
            </div>
            <div class="report-floating__footer">
              <span class="report-footer-tip">提示：点击空白处、按 Esc 或 × 均可关闭</span>
              <el-button type="primary" size="small" @click="closeReport">关闭</el-button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, onErrorCaptured } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPosition, deletePosition } from '../api/positions'
import { uploadResumes, parseResume } from '../api/resumes'
import { runMatch, batchMatch, getPositionMatches } from '../api/match'
import { getCandidates, updateCandidate, deleteCandidate, batchDeleteCandidates, getCandidate } from '../api/candidates'
import { getWorkflowRoles, workflowMatchAll, workflowMatch as workflowMatchSingle } from '../api/workflow'
import { getScoreColor, getScoreLevel, STATUS_COLORS } from '../utils/constants'
import { copyText } from '../utils/clipboard'
import { renderSafeMarkdown } from '../utils/safeMarkdown'

const route = useRoute()
const router = useRouter()
const positionId = route.params.id

const position = ref({})
const candidates = ref([])
const uploadRef = ref(null)
const uploading = ref(false)
const matching = ref(false)
const candidateLoading = ref(false)
const selectedIds = ref([])

// 评估角色
const builtinRoles = ref({})
const customRoles = ref([])
const selectedRoleId = ref('')
const currentRoleName = computed(() => {
  if (selectedRoleId.value.startsWith('builtin_')) {
    const key = selectedRoleId.value.replace('builtin_', '')
    return builtinRoles.value[key]?.name || '内置角色'
  }
  const custom = customRoles.value.find(r => String(r.id) === selectedRoleId.value)
  return custom?.name || '自定义角色'
})

// 匹配结果汇总
const matchSummary = ref({ show: false, total: 0, success: 0, failed: 0, avg: 0 })

// 报告弹窗
const reportDialog = reactive({ visible: false, data: null, analysis: '', dim_scores: null, position: { top: '0px', left: '0px' } })

const uploadProgress = ref({
  show: false,
  percent: 0,
  status: '',
  text: ''
})

const selectedFiles = ref([])
const uploadFilesCount = computed(() => selectedFiles.value.length)

const uploadFileNames = computed(() => {
  const files = selectedFiles.value
  if (files.length <= 3) {
    return files.map(f => f.name).join('、')
  }
  return `${files.slice(0, 3).map(f => f.name).join('、')} 等${files.length}个文件`
})

const allCandidateIds = computed(() => candidates.value.map(item => item.id))
const isAllSelected = computed(() => allCandidateIds.value.length > 0 && allCandidateIds.value.every(id => selectedIds.value.includes(id)))
const isIndeterminate = computed(() => selectedIds.value.length > 0 && !isAllSelected.value)

function handleFileChange(file, fileList) {
  selectedFiles.value = fileList
}

function handleFileRemove(file, fileList) {
  selectedFiles.value = fileList
}

async function handleUpload() {
  const files = selectedFiles.value
  if (!files || files.length === 0) {
    ElMessage.warning('请先选择简历文件')
    return
  }

  uploading.value = true
  uploadProgress.value = { show: true, percent: 0, status: '', text: '正在上传文件...' }

  try {
    const formData = new FormData()
    files.forEach(f => {
      formData.append('files', f.raw)
    })

    const results = await uploadResumes(formData, positionId)
    const successCount = (results || []).filter(r => !r.error).length
    const failCount = (results || []).filter(r => r.error).length

    uploadProgress.value = { show: true, percent: 30, status: '', text: `上传完成：${successCount}个成功${failCount > 0 ? '，' + failCount + '个失败' : ''}，开始AI解析...` }

    if (failCount > 0) {
      const errors = (results || []).filter(r => r.error).map(r => `${r.filename}: ${r.error}`).join('；')
      ElMessage.warning(`部分文件上传失败：${errors}`)
    }

    const successResults = (results || []).filter(r => !r.error)
    // 分离出文本为空的文件（这些不需要尝试解析，直接标记）
    const emptyTextResults = successResults.filter(r => r.text_empty)
    const normalResults = successResults.filter(r => !r.text_empty)

    if (emptyTextResults.length > 0) {
      const names = emptyTextResults.map(r => r.filename).join('、')
      ElMessage.warning(`以下文件未提取到文本内容（可能是扫描版PDF）：${names}`)
    }

    let parsedCount = 0
    const parseErrors = []
    for (let i = 0; i < normalResults.length; i++) {
      const r = normalResults[i]
      try {
        await parseResume(r.id)
        parsedCount++
        const pct = 30 + Math.round((i + 1) / normalResults.length * 55)
        uploadProgress.value = { show: true, percent: pct, status: '', text: `AI解析中... (${parsedCount}/${normalResults.length})` }
      } catch (e) {
        const errMsg = e?.response?.data?.detail || e?.message || '未知错误'
        parseErrors.push(`${r.filename}: ${errMsg}`)
      }
    }

    // 汇总结果
    const totalCount = results ? results.length : 0
    const failUpload = (results || []).filter(r => r.error).length
    const failParse = parseErrors.length
    const skipEmpty = emptyTextResults.length

    let summaryText = `完成！上传${totalCount}份`
    if (parsedCount > 0) summaryText += `，解析成功${parsedCount}份`
    if (skipEmpty > 0) summaryText += `，文本为空${skipEmpty}份`
    if (failParse > 0) summaryText += `，解析失败${failParse}份`
    if (failUpload > 0) summaryText += `，上传失败${failUpload}份`

    const finalStatus = (failParse > 0 || skipEmpty > 0) ? '' : 'success'
    uploadProgress.value = { show: true, percent: 100, status: finalStatus, text: summaryText }

    // 展示解析失败的详情
    if (parseErrors.length > 0) {
      setTimeout(() => {
        ElMessage.error({ message: `${parseErrors.length}份简历解析失败`, duration: 5000 })
      }, 500)
    }

    if (emptyTextResults.length > 0 && normalResults.length === 0) {
      ElMessage.info({
        message: '所有简历都未提取到文字，请检查PDF是否为扫描版/图片型（可先用Word重新排版后上传）',
        duration: 6000,
      })
    }
    uploadRef.value.clearFiles()
    selectedFiles.value = []
    await fetchData()

    setTimeout(() => {
      uploadProgress.value = { show: false, percent: 0, status: '', text: '' }
    }, 3000)
  } catch {
    uploadProgress.value = { show: true, percent: 0, status: 'exception', text: '上传失败，请重试' }
  } finally {
    uploading.value = false
  }
}

async function fetchData() {
  candidateLoading.value = true
  try {
    // positionId 可能是字符串，确保转成 int
    const pidNum = Number(positionId) || positionId
    const [posRes, matches, candRes] = await Promise.allSettled([
      getPosition(pidNum),
      getPositionMatches(pidNum).catch(() => []),
      getCandidates({ position_id: pidNum, page_size: 500, sort_by: 'match_score' }),
    ])

    if (posRes.status === 'fulfilled') {
      position.value = posRes.value || {}
    } else {
      console.error('加载职位失败', posRes.reason)
      position.value = {}
    }

    const matchesList = matches.status === 'fulfilled' ? (matches.value || []) : []
    const matchMap = {}
    const analysisMap = {}
    ;(matchesList || []).forEach(m => {
      matchMap[m.candidate_id] = m.score
      // 解析分析文本里的"相关经验"标记
      if (m.analysis) {
        const expMatch = m.analysis.match(/\[HAS_RELEVANT_EXP\](true|false)\[\/HAS_RELEVANT_EXP\]/)
        if (expMatch) {
          analysisMap[m.candidate_id] = { has_relevant_experience: expMatch[1] === 'true' }
        }
      }
    })

    let candList = []
    if (candRes.status === 'fulfilled') {
      candList = (candRes.value && candRes.value.items) || candRes.value || []
    } else {
      console.error('加载候选人失败', candRes.reason)
    }

    candidates.value = candList.map(c => ({
      ...c,
      match_score: matchMap[c.id] ?? c.match_score ?? null,
      has_relevant_experience: analysisMap[c.id]?.has_relevant_experience ?? null
    }))
    selectedIds.value = selectedIds.value.filter(id => candidates.value.some(item => item.id === id))
  } catch (e) {
    console.error('fetchData 出现未捕获错误', e)
    pageError.value = e?.message || '加载失败'
  } finally {
    candidateLoading.value = false
  }
}

function buildRoleConfig() {
  if (!selectedRoleId.value) return null
  if (selectedRoleId.value.startsWith('builtin_')) {
    return { builtin_role_type: selectedRoleId.value.replace('builtin_', '') }
  }
  return { custom_role_id: Number(selectedRoleId.value) }
}

async function handleSingleMatch(row) {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先在上方选择评估角色')
    return
  }
  row._matching = true
  try {
    const results = await workflowMatchSingle({
      position_id: Number(positionId),
      candidate_ids: [row.id],
      role_config: buildRoleConfig(),
    })
    if (results?.[0]?.error) {
      ElMessage.error('匹配失败: ' + results[0].error)
    } else {
      const score = results?.[0]?.score
      ElMessage.success(`「${currentRoleName.value}」打分完成: ${score || '—'}分`)
      // 直接打开报告弹窗
      reportDialog.data = row
      reportDialog.analysis = results?.[0]?.analysis || ''
      reportDialog.dim_scores = results?.[0]?.dimension_scores || null
      reportDialog.visible = true
      // 解析相关经验标记
      const expMatch = (results?.[0]?.analysis || '').match(/\[HAS_RELEVANT_EXP\](true|false)\[\/HAS_RELEVANT_EXP\]/)
      if (expMatch) {
        row.has_relevant_experience = expMatch[1] === 'true'
      }
    }
    await fetchData()
  } catch {
    // 错误已在拦截器处理
  } finally {
    row._matching = false
  }
}

async function handleBatchMatch() {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先在上方选择评估角色')
    return
  }
  matching.value = true
  try {
    const res = await workflowMatchAll({
      position_id: Number(positionId),
      role_config: buildRoleConfig(),
      min_score: 0,
    })
    const failedCount = res.failed_count ?? (res.total_count - res.matched_count)
    matchSummary.value = {
      show: true,
      total: res.total_count,
      success: res.matched_count,
      failed: failedCount,
      failedReasons: res.failed_reasons || [],
      avg: res.avg_score,
    }
    if (failedCount > 0) {
      const reasonText = (res.failed_reasons || []).slice(0, 3).join('；')
      ElMessage.warning(
        `「${currentRoleName.value}」打分完成：成功 ${res.matched_count} 人，失败 ${failedCount} 人。失败原因：${reasonText}` +
        (res.failed_reasons?.length > 3 ? '（仅显示前3条）' : '')
      )
    } else {
      ElMessage.success(`「${currentRoleName.value}」打分完成: 命中 ${res.matched_count}/${res.total_count}, 平均分 ${res.avg_score}`)
    }
    await fetchData()
  } catch {
    // 错误已在拦截器处理
  } finally {
    matching.value = false
  }
}

async function openReportDialog(row) {
  // 通过候选人详情接口拉取完整 match_result
  try {
    const detail = await getCandidate(row.id)
    reportDialog.data = { ...row, match_score: detail?.match_score ?? row.match_score }
    reportDialog.analysis = detail?.match_result?.analysis || '暂无分析内容，请重新打分后查看'
    reportDialog.dim_scores = detail?.dimension_scores || null
    // 直接居中显示浮层（位置固定在视口中央，与候选人卡片位置无关）
    positionReportCenter()
    reportDialog.visible = true
  } catch {
    // 静默失败
  }
}

// 候选人卡片 ref 集合（保留用于卡片高亮）
const candidateRefs = {}
function setCandidateRef(id, el) {
  if (el) candidateRefs[id] = el
}

// 把报告浮层定位在视口正中央
function positionReportCenter() {
  const floatWidth = Math.min(760, window.innerWidth - 40)
  const floatHeight = Math.min(window.innerHeight - 80, 560)
  const left = (window.innerWidth - floatWidth) / 2
  const top = (window.innerHeight - floatHeight) / 2
  reportDialog.position = {
    top: top + 'px',
    left: left + 'px',
    width: floatWidth + 'px',
    maxHeight: floatHeight + 'px'
  }
}

function closeReport() {
  reportDialog.visible = false
}

// 监听 ESC 关闭
function handleReportKeydown(e) {
  if (e.key === 'Escape' && reportDialog.visible) closeReport()
}

function renderMarkdown(text) {
  return renderSafeMarkdown(text, { stripMatchMarkers: true })
}

// 加载评估角色列表
async function loadRoles() {
  try {
    const res = await getWorkflowRoles()
    builtinRoles.value = {}
    for (const r of res.roles) {
      if (r.is_builtin) builtinRoles.value[r.role_key] = r
    }
    customRoles.value = res.roles.filter(r => !r.is_builtin)
    // 默认选中第一个内置角色
    if (!selectedRoleId.value) {
      const firstKey = Object.keys(builtinRoles.value)[0]
      if (firstKey) selectedRoleId.value = 'builtin_' + firstKey
    }
  } catch (e) { console.error('加载角色失败', e) }
}

// 页面级错误兜底（防止某个数据导致模板渲染抛错让整页白屏）
const pageError = ref('')
onErrorCaptured((err) => {
  console.error('[PositionDetailView 捕获渲染错误]', err)
  pageError.value = err?.message || String(err)
  return false  // 不再向上冒泡
})
function reload() { window.location.reload() }

async function handleStatusChange(row, status) {
  try {
    await updateCandidate(row.id, { status })
    row.status = status
    ElMessage.success('状态已更新')
  } catch {
    // 错误已在拦截器处理
  }
}

function toggleSelect(id, checked) {
  if (checked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter(item => item !== id)
  }
}

function toggleSelectAll(checked) {
  selectedIds.value = checked ? [...allCandidateIds.value] : []
}

async function handleBatchDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条记录吗？`, '批量删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await batchDeleteCandidates(selectedIds.value)
    ElMessage.success('批量删除完成')
    selectedIds.value = []
    await fetchData()
  } catch {
    // 取消删除
  }
}

async function handleDeleteCandidate(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」的上传记录与解析数据吗？`, '删除记录', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteCandidate(row.id)
    selectedIds.value = selectedIds.value.filter(id => id !== row.id)
    ElMessage.success('记录已删除')
    await fetchData()
  } catch {
    // 取消删除
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确认删除此职位吗？相关候选人数据将保留。', '删除确认', { type: 'warning' })
    await deletePosition(positionId)
    router.push('/positions')
  } catch { /* 取消 */ }
}

onMounted(() => {
  try {
    fetchData()
    loadRoles()
    // 全局监听 ESC
    document.addEventListener('keydown', handleReportKeydown)
  } catch (e) {
    console.error('onMounted 异常', e)
    pageError.value = e?.message || '页面初始化失败'
  }
})

// 离开页面清理事件监听
onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleReportKeydown)
})
</script>
