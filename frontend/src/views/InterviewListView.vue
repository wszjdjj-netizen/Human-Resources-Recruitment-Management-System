<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header page-hero">
      <div>
        <span class="eyebrow">Interviews</span>
        <h2>面试管理</h2>
        <p class="text-muted">预约、跟踪与总结候选人的每一次面试</p>
      </div>
      <div class="hero-actions">
        <el-button
          type="danger"
          plain
          :disabled="selectedIds.length === 0"
          @click="handleBatchDelete"
        >
          <el-icon><Delete /></el-icon>
          <span>删除选中{{ selectedIds.length ? `（${selectedIds.length}）` : '' }}</span>
        </el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          <span>新建面试</span>
        </el-button>
      </div>
    </div>

    <!-- 筛选区 -->
    <el-card class="glass-card" style="margin-bottom: 16px;">
      <el-form inline :model="filters" @submit.prevent>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 140px">
            <el-option
              v-for="opt in INTERVIEW_STATUS_LIST"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="候选人姓名 / 标题"
            clearable
            style="width: 220px"
            @keyup.enter="fetchList"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchList">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card class="glass-card">
      <el-table
        :data="filteredRows"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="44" />
        <el-table-column label="面试" min-width="220">
          <template #default="{ row }">
            <div class="title-cell">
              <span class="title">{{ row.title || '面试' }}</span>
              <span class="sub">
                {{ row.candidate?.name || '-' }} · {{ row.position?.title || '通用岗位' }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="平台" width="100" align="left">
          <template #default="{ row }">
            <el-tag effect="plain" :style="{ borderColor: getPlatformColor(row.platform), color: getPlatformColor(row.platform) }">
              {{ getPlatformLabel(row.platform) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="约定时间" width="150" align="left">
          <template #default="{ row }">
            <div>{{ formatDateTime(row.scheduled_at) }}</div>
            <div class="text-muted" style="font-size: 12px;">{{ row.duration_minutes }} 分钟</div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="90" align="left">
          <template #default="{ row }">
            <el-tag :type="INTERVIEW_STATUS_COLORS[row.status]">{{ row.status }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="创建人" width="90" align="left">
          <template #default="{ row }">
            <span class="text-muted">{{ row.creator?.full_name || row.creator?.username || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="230" fixed="right" align="left">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button size="small" link @click="goDetail(row)">详情</el-button>
              <el-button
                v-if="row.status === '已预约'"
                size="small"
                type="primary"
                @click="handleStart(row)"
              >开始</el-button>
              <el-button size="small" link @click="openEdit(row)">编辑</el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无面试" />
        </template>
      </el-table>
    </el-card>

    <!-- 新建 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑面试' : '新建面试'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-width="92px" ref="formRef" :rules="rules" class="interview-form">
        <el-form-item label="候选人" prop="candidate_id">
          <el-select v-model="form.candidate_id" filterable placeholder="选择候选人" style="width: 100%" :disabled="editing">
            <el-option
              v-for="c in candidates"
              :key="c.id"
              :label="`${c.name} · ${c.current_position || '-'}`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关联岗位">
          <el-select v-model="form.position_id" clearable placeholder="可选" style="width: 100%">
            <el-option
              v-for="p in positions"
              :key="p.id"
              :label="`${p.title} · ${p.department || ''}`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="会议平台" prop="platform">
          <el-select v-model="form.platform" style="width: 100%">
            <el-option
              v-for="p in platforms"
              :key="p.value"
              :label="p.label"
              :value="p.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="会议链接" prop="meeting_url">
          <el-input v-model="form.meeting_url" placeholder="https://meeting.xxx.com/j/xxx" />
        </el-form-item>
        <el-form-item label="约定时间" prop="scheduled_at">
          <el-date-picker
            v-model="form.scheduled_at"
            type="datetime"
            placeholder="选择时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="时长">
          <div class="duration-field">
            <el-input-number v-model="form.duration_minutes" :min="15" :max="240" :step="15" />
            <span class="duration-unit">分钟</span>
          </div>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="留空将自动生成" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import {
  listInterviews,
  createInterview,
  updateInterview,
  deleteInterview,
  startInterview,
  getInterviewPlatforms,
} from '../api/interviews'
import { getCandidates } from '../api/candidates'
import { getPositions } from '../api/positions'
import { INTERVIEW_STATUS_LIST, INTERVIEW_STATUS_COLORS } from '../utils/constants'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const candidates = ref([])
const positions = ref([])
const platforms = ref([])

const filters = reactive({ status: '', keyword: '' })
const filteredRows = computed(() => rows.value)

// 批量删除选中
const selectedIds = ref([])
function handleSelectionChange(selection) {
  selectedIds.value = selection.map(r => r.id)
}

const dialogVisible = ref(false)
const editing = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const form = reactive({
  candidate_id: null,
  position_id: null,
  platform: 'feishu',
  meeting_url: '',
  scheduled_at: '',
  duration_minutes: 60,
  title: '',
})
const rules = {
  candidate_id: [{ required: true, message: '请选择候选人', trigger: 'change' }],
  platform: [{ required: true, message: '请选择会议平台', trigger: 'change' }],
  meeting_url: [{ required: true, message: '请填写会议链接', trigger: 'blur' }],
  scheduled_at: [{ required: true, message: '请选择约定时间', trigger: 'change' }],
}

async function fetchList() {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    rows.value = await listInterviews(params)
  } finally {
    loading.value = false
  }
}

async function fetchOptions() {
  try {
    const [cs, ps, pfs] = await Promise.all([
      getCandidates({ page: 1, page_size: 200 }),
      getPositions(),
      getInterviewPlatforms(),
    ])
    candidates.value = cs.items || cs
    positions.value = ps.items || ps
    platforms.value = pfs
  } catch (e) {
    // 静默失败
  }
}

function resetFilters() {
  filters.status = ''
  filters.keyword = ''
  fetchList()
}

function openCreate() {
  editing.value = false
  editingId.value = null
  Object.assign(form, {
    candidate_id: null,
    position_id: null,
    platform: 'feishu',
    meeting_url: '',
    scheduled_at: '',
    duration_minutes: 60,
    title: '',
  })
  dialogVisible.value = true
}

function openEdit(row) {
  editing.value = true
  editingId.value = row.id
  Object.assign(form, {
    candidate_id: row.candidate_id,
    position_id: row.position_id || null,
    platform: row.platform,
    meeting_url: row.meeting_url,
    scheduled_at: row.scheduled_at?.replace(' ', 'T').slice(0, 19),
    duration_minutes: row.duration_minutes,
    title: row.title || '',
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (editing.value) {
      await updateInterview(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createInterview(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除面试「${row.title}」？此操作不可恢复。`, '提示', {
    type: 'warning',
  })
  await deleteInterview(row.id)
  ElMessage.success('已删除')
  fetchList()
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return
  await ElMessageBox.confirm(
    `确认删除选中的 ${selectedIds.value.length} 场面试？此操作不可恢复。`,
    '批量删除',
    { type: 'warning' },
  )
  // 串行删除，简单可控
  let ok = 0
  for (const id of selectedIds.value) {
    try {
      await deleteInterview(id)
      ok += 1
    } catch (e) {
      // 单条失败不影响其他
    }
  }
  ElMessage.success(`已删除 ${ok} 场面试`)
  selectedIds.value = []
  fetchList()
}

async function handleStart(row) {
  await ElMessageBox.confirm(`确定开始这场面试？开始后状态会切换为「进行中」。`, '提示', {
    type: 'info',
  })
  await startInterview(row.id)
  ElMessage.success('面试已开始')
  router.push(`/interviews/${row.id}`)
}

function goDetail(row) {
  router.push(`/interviews/${row.id}`)
}

function formatDateTime(iso) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 16)
}

function getPlatformLabel(value) {
  const p = platforms.value.find(x => x.value === value)
  return p?.label || value
}

function getPlatformColor(value) {
  const p = platforms.value.find(x => x.value === value)
  return p?.color || '#909399'
}

// ============ 到点提醒：每 60s 扫一次 ============
let remindTimer = null
const remindedIds = new Set()

function checkReminders() {
  const now = Date.now()
  rows.value.forEach((row) => {
    if (row.status !== '已预约') return
    if (remindedIds.has(row.id)) return
    const t = new Date(row.scheduled_at).getTime()
    // 提前 5 分钟到约定时间 5 分钟之内
    if (now >= t - 5 * 60 * 1000 && now <= t + 5 * 60 * 1000) {
      remindedIds.add(row.id)
      ElMessage({
        type: 'info',
        message: `候选人「${row.candidate?.name}」的面试已到点，是否前往开始？`,
        duration: 0,
        showClose: true,
        onClick: () => {
          router.push(`/interviews/${row.id}`)
        },
      })
    }
  })
}

onMounted(() => {
  fetchOptions()
  fetchList()
  remindTimer = setInterval(checkReminders, 60 * 1000)
})
onUnmounted(() => {
  if (remindTimer) clearInterval(remindTimer)
})
</script>

<style scoped>
.title-cell { display: flex; flex-direction: column; gap: 2px; }
.title { font-weight: 600; color: #1f2d3d; }
.sub { font-size: 12px; color: #6b7785; }

.interview-form :deep(.el-form-item__label) {
  white-space: nowrap;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.row-actions .el-button { padding: 4px 8px; }

.duration-field {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.duration-unit {
  color: #606266;
  font-size: 14px;
  white-space: nowrap;
}
</style>
