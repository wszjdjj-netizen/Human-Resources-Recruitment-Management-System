<template>
  <div class="page-container" v-loading="loading">
    <!-- 顶部 hero -->
    <div class="page-header page-hero interview-hero">
      <div class="hero-main">
        <div>
          <span class="eyebrow">Interview Live</span>
          <h2>{{ interview.title || '面试详情' }}</h2>
          <p class="text-muted">
            {{ interview.candidate?.name || '-' }} ·
            {{ interview.position?.title || '通用岗位' }} ·
            安排于 {{ formatDateTime(interview.scheduled_at) }}
          </p>
        </div>
        <div class="hero-actions">
          <el-tag :type="INTERVIEW_STATUS_COLORS[interview.status]" size="large" effect="dark">
            {{ interview.status }}
          </el-tag>
        </div>
      </div>
      <div class="hero-actions">
        <el-button @click="$router.push('/interviews')">
          <el-icon><Back /></el-icon>
          <span>返回列表</span>
        </el-button>
        <el-button
          v-if="interview.status === '已预约'"
          type="primary"
          @click="handleStart"
        >
          <el-icon><VideoPlay /></el-icon>
          <span>开始面试</span>
        </el-button>
        <el-button
          v-if="canEnd"
          type="warning"
          @click="handleEnd"
        >
          <el-icon><VideoPause /></el-icon>
          <span>结束面试</span>
        </el-button>
        <el-button
          v-if="canSummarize"
          type="success"
          :loading="summarizing"
          @click="handleSummarize"
        >
          <el-icon><MagicStick /></el-icon>
          <span>生成 AI 总结</span>
        </el-button>
      </div>
    </div>

    <div class="live-grid">
      <!-- 左侧：候选人 / 会议 / 笔记 -->
      <div class="left-col">
        <el-card class="glass-card" style="margin-bottom: 16px;">
          <template #header>
            <div class="card-head">
              <strong>候选人</strong>
              <el-button
                v-if="interview.candidate?.id"
                text
                size="small"
                @click="$router.push(`/candidates/${interview.candidate.id}`)"
              >查看完整简历</el-button>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="姓名">
              {{ interview.candidate?.name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="当前职位">
              {{ interview.candidate?.current_position || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="当前公司">
              {{ interview.candidate?.current_company || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="工作年限">
              {{ interview.candidate?.work_years || 0 }} 年
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="glass-card" style="margin-bottom: 16px;">
          <template #header><strong>会议信息</strong></template>
          <el-form label-width="92px" :model="interview">
            <el-form-item label="平台">
              <el-tag :style="{ borderColor: platformColor, color: platformColor }" effect="plain">
                {{ platformLabel }}
              </el-tag>
            </el-form-item>
            <el-form-item label="会议链接">
              <a v-if="interview.meeting_url" :href="interview.meeting_url" target="_blank" rel="noopener" class="meeting-link">
                {{ interview.meeting_url }}
                <el-icon><Promotion /></el-icon>
              </a>
              <span v-else class="text-muted">-</span>
            </el-form-item>
            <el-form-item label="时长">
              {{ interview.duration_minutes }} 分钟
            </el-form-item>
            <el-form-item v-if="interview.started_at" label="实际开始">
              {{ formatDateTime(interview.started_at) }}
            </el-form-item>
            <el-form-item v-if="interview.ended_at" label="实际结束">
              {{ formatDateTime(interview.ended_at) }}
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="glass-card">
          <template #header>
            <div class="card-head">
              <strong>HR 协作笔记</strong>
              <span class="text-muted" style="font-size: 12px;">所有 HR 可见，按时间追加</span>
            </div>
          </template>
          <el-input
            v-model="noteDraft"
            type="textarea"
            :rows="3"
            placeholder="写下你这一轮的观察，例如：候选人沟通清晰，但对 Q4 的高并发方案未深入..."
          />
          <div style="margin-top: 8px; text-align: right;">
            <el-button type="primary" :loading="savingNote" :disabled="!noteDraft.trim()" @click="handleAddNote">
              追加
            </el-button>
          </div>
          <el-divider />
          <div v-if="!record?.notes" class="text-muted">暂无笔记</div>
          <pre v-else class="notes-box">{{ record.notes }}</pre>
        </el-card>
      </div>

      <!-- 右侧：实时转写 + 总结 -->
      <div class="right-col">
        <el-card class="glass-card transcript-card" v-loading="transcriptLoading">
          <template #header>
            <div class="card-head">
              <div class="flex-center">
                <span class="rec-dot" :class="{ live: isRecording }"></span>
                <strong>实时转写</strong>
                <span v-if="isRecording" class="text-muted" style="font-size: 12px;">
                  · 录制中
                </span>
                <span v-else-if="interview.status === '已总结'" class="text-muted" style="font-size: 12px;">
                  · 已结束
                </span>
              </div>
              <div>
                <el-button
                  v-if="interview.status === '已预约'"
                  size="small"
                  @click="handleStart"
                >开始模拟转写</el-button>
              </div>
            </div>
          </template>

          <div v-if="!transcript.length" class="empty-transcript">
            <el-empty
              :description="interview.status === '已预约' ? '点击「开始模拟转写」启动' : '转写内容尚未生成'"
              :image-size="100"
            />
          </div>
          <div v-else class="transcript-list" ref="transcriptListRef">
            <div
              v-for="(line, idx) in transcript"
              :key="idx"
              class="transcript-line"
              :class="{ 'line-interviewer': line.speaker === '面试官', 'line-candidate': line.speaker === '候选人' }"
            >
              <div class="speaker">{{ line.speaker }}</div>
              <div class="bubble" :class="{ newest: idx === transcript.length - 1 && isRecording }">
                {{ line.text }}
              </div>
            </div>
          </div>
        </el-card>

        <el-card class="glass-card" style="margin-top: 16px;" v-if="hasSummary">
          <template #header>
            <div class="card-head">
              <strong>AI 总结报告</strong>
              <div>
                <el-tag v-if="record?.summarized_at" type="info" effect="plain" style="margin-right: 8px;">
                  生成于 {{ formatDateTime(record.summarized_at) }} · {{ record.summarized_by }}
                </el-tag>
                <el-tag :type="RECOMMENDATION_COLORS[summary?.recommendation] || 'info'">
                  {{ summary?.recommendation || '待定' }}
                </el-tag>
              </div>
            </div>
          </template>

          <div class="summary-meta">
            <div class="score-ring" :style="{ '--p': summary?.score || 0, '--color': getScoreColor(summary?.score || 0) }">
              <div class="score-num">{{ summary?.score ?? '-' }}</div>
              <div class="score-lbl">综合分</div>
            </div>
            <p class="overall">{{ summary?.overall }}</p>
          </div>

          <el-row :gutter="16">
            <el-col :span="12">
              <div class="summary-block">
                <div class="block-title block-pos">优势</div>
                <ul>
                  <li v-for="(h, i) in summary?.highlights || []" :key="`h${i}`">{{ h }}</li>
                </ul>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="summary-block">
                <div class="block-title block-neg">风险点</div>
                <ul>
                  <li v-for="(r, i) in summary?.risks || []" :key="`r${i}`">{{ r }}</li>
                </ul>
              </div>
            </el-col>
          </el-row>

          <div class="summary-block" style="margin-top: 12px;">
            <div class="block-title">建议追问</div>
            <ol>
              <li v-for="(q, i) in summary?.questions || []" :key="`q${i}`">{{ q }}</li>
            </ol>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, VideoPlay, VideoPause, MagicStick, Promotion } from '@element-plus/icons-vue'
import {
  getInterview,
  startInterview,
  endInterview,
  summarizeInterview,
  appendNotes,
  getMockScript,
  getInterviewPlatforms,
} from '../api/interviews'
import { INTERVIEW_STATUS_COLORS, RECOMMENDATION_COLORS, getScoreColor } from '../utils/constants'

const route = useRoute()
const router = useRouter()
const interviewId = route.params.id

const loading = ref(false)
const transcriptLoading = ref(false)
const interview = ref({})
const record = ref(null)
const transcript = ref([])
const summary = ref(null)
const noteDraft = ref('')
const savingNote = ref(false)
const summarizing = ref(false)
const platforms = ref([])
const transcriptListRef = ref(null)

let scriptTimer = null
let currentScript = []
let scriptIndex = 0
const isRecording = ref(false)

const canEnd = computed(() => interview.value.status === '进行中' || interview.value.status === '转写中')
const canSummarize = computed(() => {
  return ['进行中', '转写中', '已总结'].includes(interview.value.status) && (record.value?.transcript || '').trim().length > 0
})
const hasSummary = computed(() => Boolean(summary.value))
const platformLabel = computed(() => platforms.value.find(p => p.value === interview.value.platform)?.label || interview.value.platform || '-')
const platformColor = computed(() => platforms.value.find(p => p.value === interview.value.platform)?.color || '#909399')

function formatDateTime(iso) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 16)
}

async function fetchPlatforms() {
  try {
    platforms.value = await getInterviewPlatforms()
  } catch {}
}

async function fetchDetail() {
  loading.value = true
  try {
    const data = await getInterview(interviewId)
    interview.value = data
    record.value = data.record || null
    if (record.value?.summary) {
      summary.value = record.value.summary
    }
    // 如果已有 transcript，展示在右侧
    if (record.value?.transcript) {
      try {
        const lines = parseTranscript(record.value.transcript)
        transcript.value = lines
      } catch {
        // 解析失败就保持空
      }
    }
  } finally {
    loading.value = false
  }
}

function parseTranscript(text) {
  // 约定 mock 写入的格式："面试官: ...\n候选人: ..."
  if (!text) return []
  return text.split('\n').filter(Boolean).map((line) => {
    const idx = line.indexOf(':')
    if (idx === -1) return { speaker: '其他', text: line }
    return {
      speaker: line.slice(0, idx).trim(),
      text: line.slice(idx + 1).trim(),
    }
  })
}

async function handleStart() {
  try {
    await ElMessageBox.confirm('开始后状态会切换为「进行中」，并将启动模拟转写。', '开始面试', { type: 'info' })
  } catch { return }
  transcriptLoading.value = true
  try {
    const updated = await startInterview(interviewId)
    interview.value = { ...interview.value, ...updated }
    summary.value = null
    record.value = null
    transcript.value = []
    await loadScriptAndPlay()
  } finally {
    transcriptLoading.value = false
  }
}

async function loadScriptAndPlay() {
  const data = await getMockScript(interviewId)
  currentScript = data.script || []
  scriptIndex = 0
  isRecording.value = true
  pushNextLine()
}

function pushNextLine() {
  if (scriptIndex >= currentScript.length) {
    isRecording.value = false
    return
  }
  transcript.value.push(currentScript[scriptIndex])
  scriptIndex += 1
  scrollToBottom()
  const delay = 1200 + Math.floor(Math.random() * 800)
  scriptTimer = setTimeout(pushNextLine, delay)
}

function scrollToBottom() {
  nextTick(() => {
    if (transcriptListRef.value) {
      transcriptListRef.value.scrollTop = transcriptListRef.value.scrollHeight
    }
  })
}

async function handleEnd() {
  try {
    await ElMessageBox.confirm('结束后面试状态切换为「转写中」，转写内容将保存。', '结束面试', { type: 'warning' })
  } catch { return }
  if (scriptTimer) clearTimeout(scriptTimer)
  isRecording.value = false
  const text = transcript.value.map(l => `${l.speaker}: ${l.text}`).join('\n')
  await endInterview(interviewId, text)
  ElMessage.success('已保存转写')
  await fetchDetail()
}

async function handleSummarize() {
  summarizing.value = true
  try {
    const res = await summarizeInterview(interviewId, {})
    summary.value = res.summary
    ElMessage.success(res.is_mock ? 'AI 未配置，已生成示例报告（演示用）' : 'AI 总结已生成')
    await fetchDetail()
  } finally {
    summarizing.value = false
  }
}

async function handleAddNote() {
  if (!noteDraft.value.trim()) return
  savingNote.value = true
  try {
    await appendNotes(interviewId, noteDraft.value.trim())
    noteDraft.value = ''
    ElMessage.success('已追加笔记')
    await fetchDetail()
  } finally {
    savingNote.value = false
  }
}

watch(() => route.params.id, (val) => {
  if (val) {
    fetchDetail()
  }
})

onMounted(() => {
  fetchPlatforms()
  fetchDetail()
})
onUnmounted(() => {
  if (scriptTimer) clearTimeout(scriptTimer)
})
</script>

<style scoped>
.interview-hero { display: flex; flex-direction: column; gap: 14px; }
.hero-main { display: flex; justify-content: space-between; align-items: flex-start; }
.live-grid {
  display: grid;
  grid-template-columns: minmax(320px, 380px) 1fr;
  gap: 16px;
}
@media (max-width: 1024px) {
  .live-grid { grid-template-columns: 1fr; }
}

.card-head { display: flex; justify-content: space-between; align-items: center; }
.flex-center { display: flex; align-items: center; gap: 8px; }

.meeting-link {
  color: #2f63ff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;
}
.meeting-link:hover { text-decoration: underline; }

.notes-box {
  background: rgba(244, 249, 255, 0.6);
  border: 1px solid rgba(78, 92, 130, 0.12);
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.7;
  color: #344054;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  max-height: 240px;
  overflow-y: auto;
}

.transcript-card { min-height: 420px; }
.empty-transcript { padding: 40px 0; }
.transcript-list {
  max-height: 480px;
  overflow-y: auto;
  padding: 4px 4px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.transcript-line { display: flex; flex-direction: column; gap: 4px; }
.transcript-line .speaker {
  font-size: 12px;
  color: #6b7785;
  font-weight: 500;
}
.transcript-line.line-interviewer { align-items: flex-start; }
.transcript-line.line-candidate { align-items: flex-end; }
.bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(244, 249, 255, 0.95);
  border: 1px solid rgba(78, 92, 130, 0.12);
  color: #1f2d3d;
  line-height: 1.7;
}
.line-candidate .bubble {
  background: linear-gradient(135deg, rgba(79, 124, 255, 0.12), rgba(18, 182, 203, 0.1));
  border-color: rgba(79, 124, 255, 0.18);
}
.bubble.newest {
  box-shadow: 0 0 0 2px rgba(79, 124, 255, 0.25);
  animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(79, 124, 255, 0.25); }
  50% { box-shadow: 0 0 0 4px rgba(79, 124, 255, 0.1); }
}

.rec-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #c0c4cc;
}
.rec-dot.live { background: #f56c6c; box-shadow: 0 0 0 0 rgba(245,108,108,0.6); animation: rec 1.4s infinite; }
@keyframes rec {
  0% { box-shadow: 0 0 0 0 rgba(245,108,108,0.6); }
  70% { box-shadow: 0 0 0 8px rgba(245,108,108,0); }
  100% { box-shadow: 0 0 0 0 rgba(245,108,108,0); }
}

.summary-meta {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 4px 16px;
}
.score-ring {
  --p: 80;
  --color: #67c23a;
  width: 84px;
  height: 84px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background:
    conic-gradient(var(--color) calc(var(--p) * 1%), rgba(78, 92, 130, 0.15) 0);
  position: relative;
}
.score-ring::before {
  content: '';
  position: absolute;
  inset: 6px;
  background: #fff;
  border-radius: 50%;
}
.score-num { font-size: 24px; font-weight: 700; color: var(--color); z-index: 1; }
.score-lbl { font-size: 11px; color: #6b7785; z-index: 1; }
.overall { color: #344054; line-height: 1.8; margin: 0; }

.summary-block {
  background: rgba(244, 249, 255, 0.55);
  border: 1px solid rgba(78, 92, 130, 0.1);
  border-radius: 10px;
  padding: 12px 14px;
  height: 100%;
}
.block-title { font-weight: 600; margin-bottom: 8px; }
.block-pos { color: #67c23a; }
.block-neg { color: #f56c6c; }
.summary-block ul, .summary-block ol { padding-left: 20px; margin: 0; color: #344054; line-height: 1.8; }
.summary-block li { margin-bottom: 4px; }
</style>
