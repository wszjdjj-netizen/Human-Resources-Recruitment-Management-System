<template>
  <div class="page-container">
    <div class="page-header page-hero">
      <div>
        <span class="eyebrow">Talent Intelligence</span>
        <h2>人才池</h2>
        <p class="text-muted">直接查看候选人的匹配评分、技能标签和当前状态。</p>
      </div>
    </div>

    <el-card class="glass-card filter-card">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="8" :lg="6">
          <el-select v-model="filters.position_id" placeholder="选择职位" clearable @change="fetchCandidates">
            <el-option v-for="p in positions" :key="p.id" :label="p.title" :value="p.id" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="6" :lg="4">
          <el-select v-model="filters.status" placeholder="候选人状态" clearable @change="fetchCandidates">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="6" :lg="5">
          <el-input v-model="filters.search" placeholder="搜索姓名/邮箱/电话" clearable @clear="fetchCandidates" @keyup.enter="fetchCandidates" />
        </el-col>
        <el-col :xs="24" :sm="4" :lg="3">
          <el-button type="primary" @click="fetchCandidates">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="glass-card candidate-console" v-loading="loading">
      <template #header>
        <div class="candidate-toolbar">
          <div>
            <strong>候选人列表</strong>
            <span class="text-muted">共 {{ pagination.total }} 人，仅显示已匹配候选人</span>
          </div>
          <div class="candidate-toolbar__actions">
            <el-checkbox
              :model-value="isAllSelected"
              :indeterminate="isIndeterminate"
              :disabled="!candidates.length"
              @change="toggleSelectAll"
            >
              全选本页
            </el-checkbox>
            <el-button type="danger" plain :disabled="!selectedIds.length" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon>
              批量删除<span v-if="selectedIds.length">（{{ selectedIds.length }}）</span>
            </el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="!candidates.length" description="暂无已匹配候选人" />

      <div v-else class="candidate-grid">
        <article v-for="row in candidates" :key="row.id" class="candidate-card">
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
            <div v-if="row.match_score != null" class="score-pill" :style="{ '--score-color': getScoreColor(row.match_score) }">
              <strong>{{ row.match_score }}</strong>
              <span>{{ getScoreLevel(row.match_score) }}</span>
            </div>
            <el-tag v-else size="small" type="info" effect="plain">未匹配</el-tag>
            <el-tag :type="STATUS_COLORS[row.status]" size="small">{{ row.status }}</el-tag>
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
              <el-tag
                v-for="skill in row.skills"
                :key="skill.id || skill.skill_name"
                size="small"
                effect="plain"
              >
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

      <div class="pager-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchCandidates"
          @current-change="fetchCandidates"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted } from 'vue'
import { getCandidates, updateCandidate, deleteCandidate, batchDeleteCandidates } from '../api/candidates'
import { getPositions } from '../api/positions'
import { getScoreColor, getScoreLevel, STATUS_COLORS, CANDIDATE_STATUS_LIST } from '../utils/constants'
import { ElMessage, ElMessageBox } from 'element-plus'
import { copyText } from '../utils/clipboard'

const candidates = ref([])
const positions = ref([])
const loading = ref(false)
const selectedIds = ref([])
const statusOptions = CANDIDATE_STATUS_LIST

const filters = reactive({
  position_id: null,
  status: '',
  search: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const pageCandidateIds = computed(() => candidates.value.map(item => item.id))
const isAllSelected = computed(() => pageCandidateIds.value.length > 0 && pageCandidateIds.value.every(id => selectedIds.value.includes(id)))
const isIndeterminate = computed(() => selectedIds.value.length > 0 && !isAllSelected.value)

async function fetchCandidates() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      sort_by: 'match_score',
      matched_only: true
    }
    if (filters.position_id) params.position_id = filters.position_id
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search
    const res = await getCandidates(params)
    candidates.value = res.items || []
    pagination.total = res.total || 0
    selectedIds.value = selectedIds.value.filter(id => candidates.value.some(item => item.id === id))
  } catch {
    candidates.value = []
  } finally {
    loading.value = false
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
  selectedIds.value = checked ? [...pageCandidateIds.value] : []
}

async function handleStatusChange(row, status) {
  try {
    await updateCandidate(row.id, { status })
    row.status = status
    ElMessage.success('状态已更新')
  } catch {}
}

async function handleDeleteCandidate(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」吗？`, '删除记录', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteCandidate(row.id)
    selectedIds.value = selectedIds.value.filter(id => id !== row.id)
    ElMessage.success('记录已删除')
    await fetchCandidates()
  } catch {}
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
    await fetchCandidates()
  } catch {}
}

onMounted(async () => {
  try {
    positions.value = await getPositions()
  } catch {
    positions.value = []
  }
  await fetchCandidates()
})
</script>
