<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header page-hero">
      <div>
        <span class="eyebrow">Candidate Detail</span>
        <h2>{{ candidate.name || '候选人详情' }}</h2>
        <p class="text-muted">{{ candidate.current_position || '-' }} · {{ candidate.current_company || '-' }}</p>
      </div>
      <div class="hero-actions">
        <el-button @click="$router.back()">返回</el-button>
      </div>
    </div>

    <el-card class="glass-card" style="margin-bottom: 16px;">
      <template #header>
        <div class="flex-between">
          <strong>候选人信息</strong>
          <el-tag v-if="candidate.match_score != null" class="score-chip" :style="{ '--score-color': getScoreColor(candidate.match_score) }" effect="plain">
            匹配度 {{ candidate.match_score }} 分
          </el-tag>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="姓名">{{ candidate.name }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ candidate.gender || '-' }}</el-descriptions-item>
        <el-descriptions-item label="年龄">{{ candidate.age || '-' }}</el-descriptions-item>
        <el-descriptions-item label="电话">
          <div class="inline-copy">
            <span class="copy-text">{{ candidate.phone || '-' }}</span>
            <el-button v-if="candidate.phone" text circle size="small" class="copy-icon-btn" @click="copyText(candidate.phone, '电话')">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          <div class="inline-copy">
            <span class="copy-text">{{ candidate.email || '-' }}</span>
            <el-button v-if="candidate.email" text circle size="small" class="copy-icon-btn" @click="copyText(candidate.email, '邮箱')">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="工作年限">{{ candidate.work_years ? candidate.work_years + '年' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="当前公司">{{ candidate.current_company || '-' }}</el-descriptions-item>
        <el-descriptions-item label="当前职位">{{ candidate.current_position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="STATUS_COLORS[candidate.status]">{{ candidate.status }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div v-if="candidate.self_evaluation" style="margin-top: 16px;">
        <strong>自我评价</strong>
        <p class="text-muted" style="margin-top: 8px;">{{ candidate.self_evaluation }}</p>
      </div>
    </el-card>

    <el-card class="glass-card" style="margin-bottom: 16px;" v-if="skills.length > 0">
      <template #header><strong>技能标签</strong></template>
      <div class="tag-cloud">
        <el-tag v-for="s in skills" :key="s.id" effect="plain">
          {{ s.skill_name }}<span v-if="s.proficiency"> · {{ s.proficiency }}</span>
        </el-tag>
      </div>
    </el-card>

    <el-card class="glass-card" style="margin-bottom: 16px;" v-if="educations.length > 0">
      <template #header><strong>教育经历</strong></template>
      <el-timeline>
        <el-timeline-item v-for="edu in educations" :key="edu.id" :timestamp="(edu.start_date || '') + ' ~ ' + (edu.end_date || '')" placement="top">
          <p><strong>{{ edu.school }}</strong></p>
          <p>{{ edu.degree }} · {{ edu.major }}</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card class="glass-card" style="margin-bottom: 16px;" v-if="experiences.length > 0">
      <template #header><strong>工作经历</strong></template>
      <el-timeline>
        <el-timeline-item v-for="exp in experiences" :key="exp.id" :timestamp="(exp.start_date || '') + ' ~ ' + (exp.end_date || '')" placement="top">
          <p><strong>{{ exp.company }}</strong></p>
          <p style="color: #2f63ff;">{{ exp.position }}</p>
          <p v-if="exp.description" class="text-muted">{{ exp.description }}</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card class="glass-card" v-if="matchResult">
      <template #header><strong>AI 匹配分析</strong></template>
      <div style="white-space: pre-wrap; color: #344054; line-height: 1.8;">
        {{ matchResult.analysis }}
      </div>
      <p class="text-muted" style="margin-top: 12px;">
        匹配时间：{{ matchResult.matched_at?.split('T')[0] || '' }}
      </p>
    </el-card>

    <el-card class="glass-card" style="margin-top: 16px;">
      <template #header>
        <div class="flex-between">
          <strong>历史面试</strong>
          <el-button type="primary" size="small" @click="openScheduleDialog">
            <el-icon><Plus /></el-icon>
            <span>安排面试</span>
          </el-button>
        </div>
      </template>

      <el-table :data="interviews" stripe v-loading="interviewLoading">
        <el-table-column label="标题" min-width="220">
          <template #default="{ row }">
            <div style="display: flex; flex-direction: column; gap: 2px;">
              <span style="font-weight: 600;">{{ row.title || '面试' }}</span>
              <span class="text-muted" style="font-size: 12px;">
                {{ row.platformLabel }} · {{ row.duration_minutes }} 分钟
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="约定时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.scheduled_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="INTERVIEW_STATUS_COLORS[row.status]">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="推荐结论" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.recommendation" :type="row.recommendation === '推荐' || row.recommendation === '强烈推荐' ? 'success' : row.recommendation === '不推荐' ? 'danger' : 'warning'">
              {{ row.recommendation }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="goInterview(row)">详情</el-button>
            <el-button
              v-if="row.status === '已预约'"
              size="small"
              type="primary"
              @click="quickStart(row)"
            >开始</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无面试安排" />
        </template>
      </el-table>
    </el-card>

    <!-- 安排面试弹窗 -->
    <el-dialog v-model="scheduleVisible" title="安排面试" width="520px">
      <el-form :model="scheduleForm" label-width="92px">
        <el-form-item label="会议平台">
          <el-select v-model="scheduleForm.platform" style="width: 100%">
            <el-option label="飞书会议" value="feishu" />
            <el-option label="腾讯会议" value="tencent" />
            <el-option label="Zoom" value="zoom" />
            <el-option label="钉钉会议" value="dingtalk" />
            <el-option label="Microsoft Teams" value="teams" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="会议链接">
          <el-input v-model="scheduleForm.meeting_url" placeholder="https://" />
        </el-form-item>
        <el-form-item label="约定时间">
          <el-date-picker
            v-model="scheduleForm.scheduled_at"
            type="datetime"
            placeholder="选择时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="时长">
          <el-input-number v-model="scheduleForm.duration_minutes" :min="15" :max="240" :step="15" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleVisible = false">取消</el-button>
        <el-button type="primary" :loading="scheduleSaving" @click="handleSchedule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCandidate } from '../api/candidates'
import { listCandidateInterviews, createInterview, getInterview } from '../api/interviews'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getScoreColor, STATUS_COLORS, INTERVIEW_STATUS_COLORS } from '../utils/constants'
import { copyText } from '../utils/clipboard'

const route = useRoute()
const router = useRouter()
const candidateId = route.params.id

const loading = ref(true)
const candidate = ref({})
const educations = ref([])
const experiences = ref([])
const skills = ref([])
const matchResult = ref(null)

// 历史面试
const interviews = ref([])
const interviewLoading = ref(false)
const scheduleVisible = ref(false)
const scheduleSaving = ref(false)
const scheduleForm = ref({
  platform: 'feishu',
  meeting_url: '',
  scheduled_at: '',
  duration_minutes: 60,
})

const PLATFORM_LABELS = {
  feishu: '飞书会议',
  tencent: '腾讯会议',
  zoom: 'Zoom',
  dingtalk: '钉钉会议',
  teams: 'Microsoft Teams',
  other: '其他',
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getCandidate(candidateId)
    candidate.value = {
      id: res.id,
      name: res.name,
      phone: res.phone,
      email: res.email,
      gender: res.gender,
      age: res.age,
      current_company: res.current_company,
      current_position: res.current_position,
      work_years: res.work_years,
      self_evaluation: res.self_evaluation,
      status: res.status,
      match_score: res.match_score ?? null
    }
    educations.value = res.educations || []
    experiences.value = res.experiences || []
    skills.value = res.skills || []
    matchResult.value = res.match_result || null
  } catch {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

async function fetchInterviews() {
  interviewLoading.value = true
  try {
    const rows = await listCandidateInterviews(candidateId)
    interviews.value = (rows || []).map(r => ({
      ...r,
      platformLabel: PLATFORM_LABELS[r.platform] || r.platform,
      recommendation: null,
    }))
    // 拉每场详情拿 recommendation
    for (const it of interviews.value) {
      try {
        const detail = await getInterview(it.id)
        it.recommendation = detail.record?.summary?.recommendation || null
      } catch {}
    }
  } finally {
    interviewLoading.value = false
  }
}

function openScheduleDialog() {
  scheduleForm.value = {
    platform: 'feishu',
    meeting_url: '',
    scheduled_at: '',
    duration_minutes: 60,
  }
  scheduleVisible.value = true
}

async function handleSchedule() {
  if (!scheduleForm.value.meeting_url || !scheduleForm.value.scheduled_at) {
    ElMessage.warning('请填写会议链接和约定时间')
    return
  }
  scheduleSaving.value = true
  try {
    await createInterview({
      candidate_id: Number(candidateId),
      position_id: candidate.value?.position_id || null,
      platform: scheduleForm.value.platform,
      meeting_url: scheduleForm.value.meeting_url,
      scheduled_at: scheduleForm.value.scheduled_at,
      duration_minutes: scheduleForm.value.duration_minutes,
    })
    ElMessage.success('已安排面试')
    scheduleVisible.value = false
    fetchInterviews()
  } finally {
    scheduleSaving.value = false
  }
}

function goInterview(row) {
  router.push(`/interviews/${row.id}`)
}

async function quickStart(row) {
  try {
    await ElMessageBox.confirm('确定开始这场面试？', '提示', { type: 'info' })
  } catch { return }
  // 由 live 页处理真正的 start
  router.push(`/interviews/${row.id}`)
}

function formatDateTime(iso) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 16)
}

onMounted(() => {
  fetchData()
  fetchInterviews()
})
</script>
