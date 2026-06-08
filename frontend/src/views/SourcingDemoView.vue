<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header page-hero sourcing-hero">
      <div>
        <span class="eyebrow">Talent Sourcing Runner</span>
        <h2>平台搜人</h2>
        <p class="text-muted">
          线上网站负责建任务、审批外联、查看日志和截图；使用者电脑上的本地浏览器 runner 负责登录 BOSS 等平台、搜索候选人、抓取并回传人才。
        </p>
      </div>
      <div class="hero-actions">
        <el-button plain @click="platformDrawer.visible = true">
          <el-icon><Connection /></el-icon>
          平台连接
        </el-button>
        <el-button plain @click="$router.push('/ai-config')">
          <el-icon><Setting /></el-icon>
          AI 配置
        </el-button>
        <el-button @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="createAndLaunchTask">
          <el-icon><VideoPlay /></el-icon>
          创建并启动
        </el-button>
      </div>
    </div>

    <div class="control-strip">
      <article class="status-tile status-tile--runner">
        <div class="status-tile__icon">
          <el-icon><Monitor /></el-icon>
        </div>
        <div class="status-tile__body">
          <div class="status-tile__label">本地执行器</div>
          <div class="status-tile__value">{{ runnerReachable ? '已连接' : '待启动' }}</div>
          <div class="text-muted">{{ runnerStatusText }}</div>
        </div>
        <div class="status-tile__actions">
          <el-input v-model="localRunnerBase" placeholder="http://127.0.0.1:18765" @blur="persistLocalRunnerBase" />
          <div class="runner-actions">
            <el-button plain :loading="runnerPackageDownloading" @click="downloadRunnerPackage">
              <el-icon><Download /></el-icon>
              下载执行器包
            </el-button>
            <el-button type="primary" plain @click="openRunnerProtocol">
              一键唤起执行器
            </el-button>
            <el-button :loading="runnerChecking" @click="checkLocalRunner">检查</el-button>
            <el-button type="primary" plain :disabled="!selectedTaskId" @click="selectedTaskId && launchTask(selectedTaskId)">
              启动当前任务
            </el-button>
          </div>
          <div class="runner-command">
            下载后：解压整个 zip -> 双击 start-local-runner.bat -> 回到这里点检查；需要网页唤起时再双击 register-runner-protocol.bat。
          </div>
        </div>
      </article>

      <article class="status-tile">
        <div class="status-tile__icon">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="status-tile__body">
          <div class="status-tile__label">AI 配置</div>
          <div class="status-tile__value">{{ aiReady ? '可用' : '待配置' }}</div>
          <div class="text-muted">抓回文本会继续走现有 AI 解析与岗位匹配。</div>
        </div>
        <div class="status-tile__actions status-tile__actions--compact">
          <el-button type="primary" plain @click="$router.push('/ai-config')">前往配置</el-button>
        </div>
      </article>

      <article class="status-tile">
        <div class="status-tile__icon">
          <el-icon><Connection /></el-icon>
        </div>
        <div class="status-tile__body">
          <div class="status-tile__label">平台连接</div>
          <div class="status-tile__value">{{ connectedPlatformsCount }} / {{ allPlatforms.length }}</div>
          <div class="text-muted">已配置 {{ connectedPlatformsText }}</div>
          <div v-if="connectedPlatformNames.length" class="connected-platform-tags">
            <el-tag v-for="name in connectedPlatformNames" :key="name" size="small" effect="plain" type="success">{{ name }}</el-tag>
          </div>
        </div>
        <div class="status-tile__actions status-tile__actions--compact">
          <el-button plain @click="platformDrawer.visible = true">管理连接</el-button>
        </div>
      </article>
    </div>

    <div class="sourcing-layout">
      <main class="workbench">
        <div class="workbench-top">
          <el-card class="glass-card create-task-card">
            <template #header>
              <div class="card-header-line">
                <div>
                  <strong>新建任务</strong>
                  <div class="text-muted">把岗位、平台和阈值定好，后面就主要盯任务状态和审批。</div>
                </div>
                <div class="hero-actions">
                  <el-button @click="createTask">仅创建</el-button>
                  <el-button type="primary" @click="createAndLaunchTask">创建并启动</el-button>
                </div>
              </div>
            </template>

            <el-form label-width="82px" class="create-task-form">
              <div class="form-grid form-grid--primary">
                <el-form-item label="岗位">
                  <el-select v-model="form.position_id" placeholder="选择开放岗位" filterable>
                    <el-option v-for="item in positions" :key="item.id" :label="item.title" :value="item.id" />
                  </el-select>
                </el-form-item>

                <el-form-item label="任务名">
                  <el-input v-model="form.name" placeholder="如：高级前端搜人" />
                </el-form-item>
              </div>

              <el-form-item label="平台">
                <el-checkbox-group v-model="form.platforms" class="platform-checks">
                  <el-checkbox v-for="item in allPlatforms" :key="item" :label="item">{{ item }}</el-checkbox>
                </el-checkbox-group>
              </el-form-item>

              <div class="form-grid">
                <el-form-item label="关键词">
                  <el-input v-model="form.keywords" placeholder="留空则默认使用岗位名" />
                </el-form-item>

                <el-form-item label="城市">
                  <el-input v-model="form.locations" placeholder="北京、上海、深圳" />
                </el-form-item>
              </div>

              <div class="form-grid form-grid--compact">
                <el-form-item label="目标人数">
                  <el-input-number v-model="form.target_count" :min="1" :max="200" />
                </el-form-item>

                <el-form-item label="最低分">
                  <el-input-number v-model="form.min_score" :min="0" :max="100" :step="5" />
                </el-form-item>

                <el-form-item label="外联">
                  <el-switch v-model="form.auto_greeting" inline-prompt active-text="待审批后发送" inactive-text="只入库" />
                </el-form-item>
              </div>

              <el-form-item label="话术">
                <el-input
                  v-model="form.greeting_template"
                  type="textarea"
                  :rows="3"
                  placeholder="可用变量：{name} {position} {skills} {current_company} {current_position} {score}"
                />
              </el-form-item>
            </el-form>
          </el-card>

          <el-card class="glass-card task-list-card">
            <template #header>
              <div class="card-header-line">
                <div>
                  <strong>任务列表</strong>
                  <div class="text-muted">点击任务查看详情与审批；可勾选多条任务后批量删除</div>
                </div>
                <div class="card-header-actions task-list-actions">
                  <el-checkbox
                    :model-value="isAllTasksSelected"
                    :indeterminate="isTasksIndeterminate"
                    :disabled="!tasks.length"
                    @change="toggleSelectAllTasks"
                  >
                    全选
                  </el-checkbox>
                  <el-button
                    type="danger"
                    plain
                    :disabled="!selectedTaskIds.length"
                    @click="handleBatchDeleteTasks"
                  >
                    <el-icon><Delete /></el-icon>
                    批量删除{{ selectedTaskIds.length ? `（${selectedTaskIds.length}）` : '' }}
                  </el-button>
                </div>
              </div>
            </template>

            <el-table
              :data="tasks"
              row-key="id"
              ref="taskTableRef"
              highlight-current-row
              :current-row-key="selectedTaskId"
              @current-change="handleCurrentTaskChange"
              @selection-change="handleTaskSelectionChange"
            >
              <el-table-column type="selection" width="48" :selectable="() => true" />
              <el-table-column prop="name" label="任务" min-width="200" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="statusTagType(row.status)">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="imported_count" label="入库" width="76" />
              <el-table-column prop="deduped_count" label="去重" width="76" />
              <el-table-column prop="contacted_count" label="已发" width="76" />
              <el-table-column label="操作" width="180">
                <template #default="{ row }">
                  <el-button size="small" @click.stop="launchTask(row.id)">启动</el-button>
                  <el-button size="small" type="danger" text @click.stop="handleDeleteTask(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <div v-if="selectedTask" class="detail-stack">
          <el-card class="glass-card">
            <template #header>
              <div class="card-header-line">
                <div>
                  <strong>{{ selectedTask.name }}</strong>
                  <div class="text-muted task-subtitle">
                    {{ selectedTask.position_title || '未命名岗位' }}
                    <span v-if="selectedTask.current_platform">· {{ selectedTask.current_platform }}</span>
                    <span v-if="selectedTask.runner_name">· {{ selectedTask.runner_name }}</span>
                  </div>
                </div>
                <div class="hero-actions">
                  <el-tag :type="statusTagType(selectedTask.status)">{{ selectedTask.status }}</el-tag>
                  <el-button size="small" type="primary" plain @click="launchTask(selectedTask.id)">重新启动</el-button>
                </div>
              </div>
            </template>

            <el-alert
              v-if="(selectedTask.status_detail || selectedTask.last_error) && !dismissedAlert"
              :title="translateError(selectedTask.last_error || selectedTask.status_detail)"
              :type="selectedTask.status === '失败' ? 'error' : 'info'"
              show-icon
              :closable="true"
              @close="dismissedAlert = true"
            />

            <div class="metric-grid">
              <div class="metric-card">
                <span class="metric-label">已审核</span>
                <strong>{{ selectedTask.reviewed_count }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">已入库</span>
                <strong>{{ selectedTask.imported_count }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">重复去重</span>
                <strong>{{ selectedTask.deduped_count }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">待审批</span>
                <strong>{{ selectedTask.pending_outreach_count }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">待发送</span>
                <strong>{{ selectedTask.approved_outreach_count }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">发送失败</span>
                <strong>{{ selectedTask.failed_outreach_count }}</strong>
              </div>
            </div>

            <div class="task-meta-grid">
              <div><span class="field-label">关键词</span><div>{{ selectedTask.keywords || '默认岗位名' }}</div></div>
              <div><span class="field-label">城市</span><div>{{ selectedTask.locations || '未限制' }}</div></div>
              <div><span class="field-label">最近心跳</span><div>{{ formatDateTime(selectedTask.last_heartbeat) }}</div></div>
              <div><span class="field-label">创建时间</span><div>{{ formatDateTime(selectedTask.created_at) }}</div></div>
            </div>
          </el-card>

          <div class="detail-grid">
            <el-card class="glass-card">
              <template #header>
                <div class="card-header-line">
                  <strong>执行日志</strong>
                  <div class="card-header-actions">
                    <span class="text-muted">{{ positionLogs.length }} 条</span>
                    <el-button
                      size="small"
                      type="danger"
                      text
                      :disabled="!positionLogs.length"
                      @click="handleClearLogs"
                    >
                      清空全部
                    </el-button>
                  </div>
                </div>
              </template>
              <el-empty v-if="!positionLogs.length" description="暂无执行日志" />
              <div v-else class="log-list">
                <div v-for="item in positionLogs" :key="item.id" class="log-item">
                  <div class="log-item__top">
                    <div class="log-item__meta">
                      <el-tag size="small" effect="plain" :type="logTagType(item.level)">{{ item.level }}</el-tag>
                      <span v-if="item.stage" class="text-muted">{{ item.stage }}</span>
                    </div>
                    <span class="text-muted">{{ formatDateTime(item.created_at) }}</span>
                    <el-button size="small" type="danger" text circle @click="handleDeleteLog(item)" style="margin-left: auto;">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <div class="log-message">{{ item.message }}</div>
                  <div v-if="item.detail" class="text-muted">{{ item.detail }}</div>
                </div>
              </div>
            </el-card>

            <el-card class="glass-card">
              <template #header>
                <div class="card-header-line">
                  <strong>执行截图</strong>
                  <div class="card-header-actions">
                    <span class="text-muted">{{ positionScreenshots.length }} 张</span>
                    <el-button
                      size="small"
                      type="danger"
                      text
                      :disabled="!positionScreenshots.length"
                      @click="handleClearScreenshots"
                    >
                      清空全部
                    </el-button>
                  </div>
                </div>
              </template>
              <el-empty v-if="!positionScreenshots.length" description="暂无截图" />
              <div v-else class="screenshot-grid">
                <article v-for="item in positionScreenshots" :key="item.id" class="screenshot-card screenshot-card--deletable">
                  <img
                    v-if="screenshotUrls[item.id]"
                    :src="screenshotUrls[item.id]"
                    :alt="item.caption || '执行截图'"
                    class="screenshot-image"
                  />
                  <div v-else class="screenshot-loading">加载中...</div>
                  <div class="screenshot-meta">
                    <strong>{{ item.caption || item.stage || '执行截图' }}</strong>
                    <div class="text-muted">{{ formatDateTime(item.created_at) }}</div>
                    <div v-if="item.source_url" class="screenshot-link">{{ item.source_url }}</div>
                  </div>
                  <button class="screenshot-delete-btn" @click="handleDeleteScreenshot(item)">
                    <el-icon><Delete /></el-icon>
                  </button>
                </article>
              </div>
            </el-card>
          </div>

          <div class="detail-grid detail-grid--approval">
            <el-card class="glass-card">
              <template #header>
                <div class="card-header-line">
                  <strong>外联审批</strong>
                  <span class="text-muted">先在这里确认，再由本地执行器发送</span>
                </div>
              </template>

              <el-empty v-if="!selectedTask.outreach?.length" description="暂无外联记录" />
              <div v-else class="outreach-list">
                <article v-for="item in selectedTask.outreach" :key="item.id" class="outreach-card">
                  <div class="outreach-card__head">
                    <div>
                      <strong>{{ item.candidate_name || `候选人 #${item.candidate_id}` }}</strong>
                      <div class="text-muted">
                        {{ item.platform }}
                        <span v-if="item.sent_at">· 已发送 {{ formatDateTime(item.sent_at) }}</span>
                      </div>
                    </div>
                    <div class="hero-actions">
                      <el-tag size="small" effect="plain" :type="reviewTagType(item.review_status)">
                        {{ item.review_status }}
                      </el-tag>
                      <el-tag size="small" effect="plain" :type="outreachStatusTagType(item.status)">
                        {{ item.status }}
                      </el-tag>
                    </div>
                  </div>

                  <div class="outreach-message">{{ item.message }}</div>
                  <div v-if="item.failure_reason" class="text-muted">失败原因：{{ item.failure_reason }}</div>

                  <div class="outreach-actions">
                    <el-button
                      v-if="item.review_status === '待确认'"
                      size="small"
                      type="primary"
                      @click="reviewOutreachItem(item, 'approve')"
                    >
                      批准发送
                    </el-button>
                    <el-button
                      v-if="item.review_status === '待确认'"
                      size="small"
                      @click="reviewOutreachItem(item, 'skip')"
                    >
                      跳过
                    </el-button>
                    <el-button
                      v-if="item.profile_url"
                      size="small"
                      plain
                      @click="openProfile(item.profile_url)"
                    >
                      打开候选人页
                    </el-button>
                  </div>
                </article>
              </div>
            </el-card>

            <el-card class="glass-card">
              <template #header>
                <div class="card-header-line">
                  <strong>外联审计</strong>
                  <span class="text-muted">{{ selectedTask.outreach_audit?.length || 0 }} 条</span>
                </div>
              </template>
              <el-empty v-if="!selectedTask.outreach_audit?.length" description="暂无审计记录" />
              <div v-else class="audit-list">
                <div v-for="item in selectedTask.outreach_audit" :key="item.id" class="audit-item">
                  <div class="audit-item__meta">
                    <strong>{{ item.action }}</strong>
                    <span class="text-muted">{{ item.actor_type }}</span>
                    <span class="text-muted">{{ formatDateTime(item.created_at) }}</span>
                  </div>
                  <div class="text-muted">{{ item.detail || '—' }}</div>
                </div>
              </div>
            </el-card>
          </div>
        </div>

        <el-empty v-else description="先创建或选择一个搜人任务" />
      </main>
    </div>

    <el-drawer v-model="platformDrawer.visible" title="平台连接" size="480px" class="platform-drawer">
      <div class="drawer-stack">
        <!-- 已配置平台概览 -->
        <div class="platform-overview">
          <div class="overview-header">
            <strong>当前已配置平台</strong>
            <el-tag size="small" type="info">{{ connectedPlatformsCount }} / {{ allPlatforms.length }}</el-tag>
          </div>
          <div v-if="connectedPlatformNames.length" class="connected-tags-row">
            <el-tag v-for="name in connectedPlatformNames" :key="name" effect="plain" type="success" class="connected-tag">{{ name }}</el-tag>
          </div>
          <el-empty v-else description="暂未配置任何平台连接" :image-size="60" />
        </div>

        <el-divider />

        <!-- 在线平台配置区 -->
        <div class="section-title">在线招聘平台</div>
        <div class="text-muted section-desc">
          配置后本地 runner 会直接复用这些登录态进行搜人。
        </div>
        <div class="platform-grid">
          <div v-for="item in platforms" :key="item.platform" class="platform-card" :class="{ 'platform-card--active': item.has_credential }">
            <div class="platform-card__head">
              <div class="platform-card__icon">
                <el-icon><Connection /></el-icon>
              </div>
              <div class="platform-card__info">
                <strong>{{ item.platform }}</strong>
                <el-tag size="small" effect="plain" :type="item.has_credential ? 'success' : 'info'">
                  {{ item.status }}
                </el-tag>
              </div>
            </div>
            <div class="text-muted platform-card__account">{{ item.account_name || '未配置账号' }}</div>
            <div class="platform-card__actions">
              <el-button size="small" :type="item.has_credential ? 'primary' : 'default'" @click="openConnectDialog(item)">
                {{ item.has_credential ? '修改配置' : '配置登录态' }}
              </el-button>
            </div>
          </div>
        </div>

        <el-divider />

        <!-- 本地连接配置区 -->
        <div class="section-title">本地执行器连接</div>
        <div class="text-muted section-desc">
          用于连接当前使用者电脑上的浏览器自动化执行器。线上使用时，127.0.0.1 指的是打开网页的这台电脑，不是服务器。
        </div>
        <div class="local-runner-config">
          <el-form label-width="100px" size="default">
            <el-form-item label="执行器地址">
              <el-input v-model="localRunnerBase" placeholder="http://127.0.0.1:18765" @blur="persistLocalRunnerBase" />
              <div class="form-tip">默认地址：http://127.0.0.1:18765</div>
            </el-form-item>
            <el-form-item label="连接状态">
              <div class="runner-status-inline">
                <el-tag :type="runnerReachable ? 'success' : 'danger'" effect="plain">
                  {{ runnerReachable ? '已连接' : '未连接' }}
                </el-tag>
                <el-button size="small" :loading="runnerChecking" @click="checkLocalRunner">检测连接</el-button>
              </div>
              <div class="text-muted form-tip">{{ runnerStatusText }}</div>
            </el-form-item>
            <el-form-item label="快速启动">
              <div class="runner-status-inline runner-status-inline--wrap">
                <el-button type="primary" plain :loading="runnerPackageDownloading" @click="downloadRunnerPackage">
                  <el-icon><Download /></el-icon>
                  下载执行器包
                </el-button>
                <el-button plain @click="openRunnerProtocol">网页一键唤起</el-button>
              </div>
              <div class="form-tip">下载后先解压整个 zip，再双击 start-local-runner.bat。需要网页一键唤起时，再双击 register-runner-protocol.bat；不要删除同目录的 register-runner-protocol.ps1。</div>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="connectDialog.visible" title="配置平台登录态" width="560px">
      <el-form label-width="88px">
        <el-form-item label="平台">
          <el-input v-model="connectDialog.form.platform" disabled />
        </el-form-item>
        <el-form-item label="账号名">
          <el-input v-model="connectDialog.form.account_name" placeholder="用于区分不同平台账号" />
        </el-form-item>
        <el-form-item label="凭据">
          <el-input
            v-model="connectDialog.form.credential"
            type="textarea"
            :rows="6"
            placeholder="粘贴登录 Cookie、OAuth Token 或平台授权凭据"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="connectDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="savePlatform">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Cpu, Delete, Download, Monitor, Refresh, Setting, VideoPlay } from '@element-plus/icons-vue'
import { getAiConfig } from '../api/aiConfig'
import { getPositions } from '../api/positions'
import {
  DEFAULT_LOCAL_RUNNER_BASE,
  clearTaskLogs,
  clearTaskScreenshots,
  createSourcingTask,
  deleteTaskLog,
  deleteTaskScreenshot,
  deleteSourcingTask,
  downloadLocalRunnerPackage,
  getPositionLogs,
  getPositionScreenshots,
  getLocalRunnerHealth,
  getSourcingPlatforms,
  getSourcingScreenshot,
  getSourcingTaskDetail,
  getSourcingTasks,
  launchSourcingTask,
  reviewOutreach,
  saveSourcingPlatform,
  wakeLocalRunner
} from '../api/sourcing'
import { LOG_LEVEL_COLORS, SOURCING_STATUS_COLORS } from '../utils/constants'

const LOCAL_RUNNER_KEY = 'local_runner_base'

const loading = ref(false)
const platforms = ref([])
const positions = ref([])
const tasks = ref([])
const selectedTask = ref(null)
const selectedTaskId = ref(null)
const aiConfig = ref(null)
const positionLogs = ref([])
const positionScreenshots = ref([])
const runnerReachable = ref(false)
const runnerStatusText = ref('尚未检测本地执行器')
const runnerChecking = ref(false)
const runnerPackageDownloading = ref(false)
const dismissedAlert = ref(false)
const screenshotUrls = reactive({})
let pollTimer = null

const allPlatforms = ['BOSS直聘', '猎聘', '领英', '脉脉']
const localRunnerBase = ref(localStorage.getItem(LOCAL_RUNNER_KEY) || DEFAULT_LOCAL_RUNNER_BASE)

const aiReady = computed(() => Boolean(aiConfig.value?.has_key && aiConfig.value?.model && aiConfig.value?.endpoint))
const connectedPlatformsCount = computed(() => platforms.value.filter((item) => item.has_credential).length)
const connectedPlatformsText = computed(() => {
  const names = platforms.value.filter((item) => item.has_credential).map((item) => item.platform)
  return names.length ? names.join('、') : '0 个平台'
})

const connectedPlatformNames = computed(() => {
  return platforms.value.filter((item) => item.has_credential).map((item) => item.platform)
})

const form = reactive({
  position_id: null,
  name: '',
  platforms: ['BOSS直聘'],
  keywords: '',
  locations: '',
  target_count: 20,
  min_score: 60,
  auto_greeting: true,
  greeting_template: '你好{name}，我是招聘负责人。看到你在{skills}方向的经历，和我们正在招聘的“{position}”比较匹配，想和你沟通一下机会。'
})

const connectDialog = reactive({
  visible: false,
  form: {
    platform: '',
    account_name: '',
    credential: ''
  }
})

const platformDrawer = reactive({
  visible: false
})

function persistLocalRunnerBase() {
  localStorage.setItem(LOCAL_RUNNER_KEY, localRunnerBase.value.trim() || DEFAULT_LOCAL_RUNNER_BASE)
}

function statusTagType(status) {
  return SOURCING_STATUS_COLORS[status] || 'info'
}

function logTagType(level) {
  return LOG_LEVEL_COLORS[level] || ''
}

function reviewTagType(status) {
  if (status === '待确认') return 'warning'
  if (status === '已批准') return 'success'
  return 'info'
}

// 把执行器/Playwright 抛出的英文/技术错误翻译成用户可读中文
function translateError(rawError) {
  if (!rawError) return ''
  const text = String(rawError)
  if (/wait_for_timeout|Target page|context or browser has been closed/i.test(text)) {
    return '本地浏览器执行器已关闭或超时（可能是浏览器进程被关闭、网络断开或平台页面有反爬验证）。请检查本地执行器窗口的报错日志后，点击「重新启动」再次发起。'
  }
  if (/Timeout|timeout/i.test(text) && /playwright|browser/i.test(text)) {
    return '本地浏览器操作超时，请确认本地执行器进程仍在运行后重试。'
  }
  if (/Connection refused|ECONNREFUSED/i.test(text)) {
    return '无法连接本地执行器（127.0.0.1:18765）。请先双击 start-local-runner.bat；如果已注册协议，也可以点击「一键唤起执行器」。'
  }
  if (/403|verify|captcha|滑块|验证码/i.test(text)) {
    return '平台要求图形验证码/扫码验证，请在本地浏览器中手动完成验证后再继续。'
  }
  return text
}

function outreachStatusTagType(status) {
  if (status === '已发送') return 'success'
  if (status === '发送失败') return 'danger'
  if (status === '已回复') return 'primary'
  return 'info'
}

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

function openConnectDialog(item) {
  connectDialog.form.platform = item.platform
  connectDialog.form.account_name = item.account_name || ''
  connectDialog.form.credential = ''
  connectDialog.visible = true
}

async function savePlatform() {
  await saveSourcingPlatform({
    platform: connectDialog.form.platform,
    account_name: connectDialog.form.account_name,
    credential: connectDialog.form.credential,
    auth_type: 'cookie'
  })
  ElMessage.success('平台登录态已保存')
  connectDialog.visible = false
  await loadPlatforms()
}

async function loadPlatforms() {
  platforms.value = await getSourcingPlatforms()
}

async function loadPositions() {
  positions.value = await getPositions({ status: '开放' })
  if (!form.position_id && positions.value.length) {
    form.position_id = positions.value[0].id
  }
}

async function loadTasks(preferredTaskId = null) {
  tasks.value = await getSourcingTasks()
  const targetId = preferredTaskId || selectedTaskId.value || tasks.value[0]?.id || null
  if (targetId) {
    const stillExists = tasks.value.some((item) => item.id === targetId)
    selectedTaskId.value = stillExists ? targetId : tasks.value[0]?.id || null
  } else {
    selectedTaskId.value = null
  }
}

async function loadTaskDetail(taskId = selectedTaskId.value) {
  if (!taskId) {
    selectedTask.value = null
    clearScreenshotUrls()
    positionLogs.value = []
    positionScreenshots.value = []
    return
  }
  const detail = await getSourcingTaskDetail(taskId)
  selectedTask.value = detail
  // 同时加载该任务自身的日志和截图（用于单任务的精确展示）
  positionLogs.value = detail.logs || []
  positionScreenshots.value = detail.screenshots || []
  await hydrateScreenshots(detail)
}

async function hydrateScreenshots(task) {
  const wantedIds = new Set((task.screenshots || []).map((item) => item.id))
  Object.keys(screenshotUrls).forEach((id) => {
    if (!wantedIds.has(Number(id))) {
      URL.revokeObjectURL(screenshotUrls[id])
      delete screenshotUrls[id]
    }
  })

  for (const item of task.screenshots || []) {
    if (screenshotUrls[item.id]) continue
    try {
      const blob = await getSourcingScreenshot(task.id, item.id)
      screenshotUrls[item.id] = URL.createObjectURL(blob)
    } catch {
      // ignore
    }
  }
}

function clearScreenshotUrls() {
  Object.values(screenshotUrls).forEach((url) => URL.revokeObjectURL(url))
  Object.keys(screenshotUrls).forEach((key) => delete screenshotUrls[key])
}

// 删除单条日志
async function handleDeleteLog(item) {
  try {
    await deleteTaskLog(selectedTask.value.id, item.id)
    positionLogs.value = positionLogs.value.filter((l) => l.id !== item.id)
    ElMessage.success('日志已删除')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// 清空当前任务的所有日志
async function handleClearLogs() {
  try {
    await ElMessageBox.confirm('确定要清空所有执行日志吗？此操作不可恢复。', '清空日志', { type: 'warning' })
    await clearTaskLogs(selectedTask.value.id)
    // 如果是按职位维度显示，重新加载
    if (form.position_id) {
      await loadPositionLogs()
    }
    ElMessage.success('日志已清空')
  } catch {
    // 用户取消
  }
}

// 删除单张截图
async function handleDeleteScreenshot(item) {
  try {
    await deleteTaskScreenshot(selectedTask.value.id, item.id)
    URL.revokeObjectURL(screenshotUrls[item.id])
    delete screenshotUrls[item.id]
    positionScreenshots.value = positionScreenshots.value.filter((s) => s.id !== item.id)
    ElMessage.success('截图已删除')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// 清空所有截图
async function handleClearScreenshots() {
  try {
    await ElMessageBox.confirm('确定要清空所有执行截图吗？此操作不可恢复。', '清空截图', { type: 'warning' })
    await clearTaskScreenshots(selectedTask.value.id)
    clearScreenshotUrls()
    if (form.position_id) {
      await loadPositionScreenshots()
    }
    ElMessage.success('截图已清空')
  } catch {
    // 用户取消
  }
}

// 按职位加载该职位下所有任务的日志（切换职位时调用）
async function loadPositionLogs() {
  if (!form.position_id) return
  try {
    positionLogs.value = await getPositionLogs(form.position_id)
  } catch {
    positionLogs.value = []
  }
}

// 按职位加载该职位下所有任务的截图
async function loadPositionScreenshots() {
  if (!form.position_id) return
  try {
    const items = await getPositionScreenshots(form.position_id)
    positionScreenshots.value = items
    // 只加载当前选中任务关联的截图图片
    hydrateScreenshots({ screenshots: items })
  } catch {
    positionScreenshots.value = []
  }
}

async function loadAiState() {
  try {
    aiConfig.value = await getAiConfig()
  } catch {
    aiConfig.value = null
  }
}

async function checkLocalRunner(options = {}) {
  persistLocalRunnerBase()
  runnerChecking.value = true
  try {
    const res = await getLocalRunnerHealth(localRunnerBase.value)
    runnerReachable.value = true
    runnerStatusText.value = `本地执行器在线，当前运行任务：${(res.active_tasks || []).join(', ') || '无'}`
    if (!options.silent) ElMessage.success('本地执行器已连接')
  } catch (error) {
    runnerReachable.value = false
    const message = normalizeLocalRunnerError(error)
    runnerStatusText.value = message
    if (!options.silent) ElMessage.warning(message)
  } finally {
    runnerChecking.value = false
  }
}

function normalizeLocalRunnerError(error) {
  const text = `${error?.message || ''} ${error?.response?.data?.detail || ''}`
  if (/Failed to fetch|NetworkError|fetch failed|ECONNREFUSED|Connection refused/i.test(text)) {
    return '未检测到本地执行器。请先下载并解压执行器包，双击 start-local-runner.bat，看到窗口显示 127.0.0.1:18765 后再点检查。'
  }
  return error?.message || '本地执行器未启动'
}

function validateTaskForm() {
  if (!form.position_id) {
    ElMessage.warning('请先选择岗位')
    return false
  }
  if (!form.platforms.length) {
    ElMessage.warning('请至少选择一个平台')
    return false
  }
  if (!aiReady.value) {
    ElMessage.warning('请先完成 AI 配置')
    return false
  }
  return true
}

async function createTask() {
  if (!validateTaskForm()) return null
  const task = await createSourcingTask({ ...form })
  ElMessage.success('搜人任务已创建')
  await loadTasks(task.id)
  await loadTaskDetail(task.id)
  return task
}

async function launchTask(taskId) {
  loading.value = true
  try {
    const payload = await launchSourcingTask(taskId)
    await sendLaunchToLocalRunner(payload, taskId)
    await loadTasks(taskId)
    await loadTaskDetail(taskId)
  } catch (error) {
    const message = error?.message || error?.response?.data?.detail || '启动本地执行器失败'
    runnerReachable.value = false
    runnerStatusText.value = '未连接到当前电脑的本地执行器，请先启动后再重试'
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

async function sendLaunchToLocalRunner(payload, taskId) {
  try {
    await wakeLocalRunner(payload, localRunnerBase.value)
  } catch (error) {
    if (!isLocalRunnerConnectionError(error)) throw error
    runnerReachable.value = false
    runnerStatusText.value = '正在尝试一键唤起本地执行器...'
    openRunnerProtocol()
    await waitForLocalRunnerReady()
    await wakeLocalRunner(payload, localRunnerBase.value)
  }

  runnerReachable.value = true
  runnerStatusText.value = `已唤起本地执行器，任务 #${taskId} 正在连接`
  ElMessage.success('本地执行器已唤起')
}

function isLocalRunnerConnectionError(error) {
  const text = `${error?.message || ''} ${error?.response?.data?.detail || ''}`
  return /Failed to fetch|fetch failed|NetworkError|ECONNREFUSED|Connection refused|本地执行器|唤起本地执行器/i.test(text)
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function waitForLocalRunnerReady() {
  for (let i = 0; i < 8; i++) {
    await sleep(i === 0 ? 1200 : 1000)
    try {
      const res = await getLocalRunnerHealth(localRunnerBase.value)
      runnerReachable.value = true
      runnerStatusText.value = `本地执行器在线，当前运行任务：${(res.active_tasks || []).join(', ') || '无'}`
      return
    } catch {
      // keep waiting
    }
  }
  throw new Error('未检测到本地执行器。请先下载并解压执行器包，双击 start-local-runner.bat；如需网页一键唤起，请先运行 register-runner-protocol.bat。')
}

async function createAndLaunchTask() {
  const task = await createTask()
  if (task?.id) {
    await launchTask(task.id)
  }
}

async function reviewOutreachItem(item, action) {
  if (!selectedTaskId.value) return
  await reviewOutreach(selectedTaskId.value, item.id, action)
  ElMessage.success(action === 'approve' ? '已批准发送' : '已跳过')
  await loadTasks(selectedTaskId.value)
  await loadTaskDetail(selectedTaskId.value)
}

// 批量删除（多选）任务
async function handleBatchDeleteTasks() {
  const ids = [...selectedTaskIds.value]
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(
      `确定要批量删除选中的 ${ids.length} 个任务吗？此操作将同时删除这些任务的所有日志、截图和外联记录，且不可恢复。`,
      '批量删除任务',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    let successCount = 0
    let failCount = 0
    const failed = []
    for (const id of ids) {
      try {
        await deleteSourcingTask(id)
        successCount++
      } catch (e) {
        failCount++
        failed.push(`#${id}: ${e?.response?.data?.detail || e?.message || '删除失败'}`)
      }
    }
    selectedTaskIds.value = []
    // 如果当前选中的任务在被删除列表里，清空详情
    if (selectedTaskId.value && ids.includes(selectedTaskId.value)) {
      selectedTaskId.value = null
      selectedTask.value = null
      clearScreenshotUrls()
      positionLogs.value = []
      positionScreenshots.value = []
    }
    await loadTasks()
    if (failCount > 0) {
      ElMessage.warning(`已删除 ${successCount} 个，失败 ${failCount} 个（${failed.join('；')}）`)
    } else {
      ElMessage.success(`已删除 ${successCount} 个任务`)
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '批量删除失败')
    }
  }
}

// 任务多选状态
const selectedTaskIds = ref([])
function handleTaskSelectionChange(selection) {
  selectedTaskIds.value = (selection || []).map((row) => row.id)
}
const allTaskIds = computed(() => tasks.value.map((t) => t.id))
const isAllTasksSelected = computed(
  () => allTaskIds.value.length > 0 && selectedTaskIds.value.length === allTaskIds.value.length
)
const isTasksIndeterminate = computed(
  () => selectedTaskIds.value.length > 0 && selectedTaskIds.value.length < allTaskIds.value.length
)
function toggleSelectAllTasks(checked) {
  // Element Plus 的 checkbox 只能控制是否全选，el-table 的 selection 仍要靠 row.toggleSelection
  // 这里通过 el-table 的 ref 实现真正的全选/取消
  const tbl = taskTableRef.value
  if (!tbl) return
  tasks.value.forEach((row) => {
    if (checked) {
      tbl.toggleRowSelection(row, true)
    } else {
      tbl.toggleRowSelection(row, false)
    }
  })
}
const taskTableRef = ref(null)

// 删除搜人任务
async function handleDeleteTask(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务「${row.name}」吗？此操作将同时删除该任务的所有日志、截图和外联记录，且不可恢复。`,
      '删除任务',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await deleteSourcingTask(row.id)
    ElMessage.success('任务已删除')
    if (selectedTaskId.value === row.id) {
      selectedTaskId.value = null
      selectedTask.value = null
      clearScreenshotUrls()
      positionLogs.value = []
      positionScreenshots.value = []
    }
    await loadTasks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '删除失败')
    }
  }
}

function handleCurrentTaskChange(row) {
  if (!row?.id) return
  selectedTaskId.value = row.id
}

function openProfile(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function downloadRunnerPackage() {
  runnerPackageDownloading.value = true
  try {
    const blob = await downloadLocalRunnerPackage()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'recruitment-local-runner.zip'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    ElMessage.success('本地执行器包已开始下载')
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '下载本地执行器包失败')
  } finally {
    runnerPackageDownloading.value = false
  }
}

function openRunnerProtocol() {
  window.location.href = 'recruitment-runner://start'
  ElMessage.info('如果浏览器询问是否打开本地程序，请选择允许。首次使用前需先运行 register-runner-protocol.bat。')
}

async function refreshAll() {
  loading.value = true
  try {
    // Promise.all 中任何一个 reject 都会让整体 reject -> 卡住 loading
    // 改用 allSettled + 内部函数自己处理异常
    await Promise.allSettled([
      loadPlatforms(), loadPositions(), loadTasks(), loadAiState(), checkLocalRunner({ silent: true })
    ])
    if (selectedTaskId.value) {
      try { await loadTaskDetail(selectedTaskId.value) } catch (e) { /* silent */ }
    }
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    try {
      await loadTasks(selectedTaskId.value)
      if (selectedTaskId.value) {
        await loadTaskDetail(selectedTaskId.value)
      }
    } catch {
      // silent
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(selectedTaskId, async (taskId) => {
  if (taskId) {
    dismissedAlert.value = false
    await loadTaskDetail(taskId)
  } else {
    selectedTask.value = null
    clearScreenshotUrls()
  }
})

// 切换职位时，自动加载该职位的所有日志和截图
watch(() => form.position_id, async (newPosId) => {
  if (newPosId && selectedTask.value?.position_id !== newPosId) {
    // 职位变了，清空当前任务选中状态，加载职位维度的日志/截图
    selectedTaskId.value = null
    selectedTask.value = null
    clearScreenshotUrls()
    await Promise.all([loadPositionLogs(), loadPositionScreenshots()])
  }
})

onMounted(async () => {
  await refreshAll()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
  clearScreenshotUrls()
})
</script>

<style scoped>
.sourcing-hero {
  align-items: center;
}

.control-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) repeat(2, minmax(260px, 0.7fr));
  gap: 16px;
  margin-bottom: 16px;
}

.status-tile {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  min-height: 128px;
  padding: 18px 20px;
  border: 1px solid rgba(255, 255, 255, 0.76);
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.56)),
    rgba(255, 255, 255, 0.6);
  box-shadow: 0 16px 44px rgba(31, 50, 88, 0.12);
  backdrop-filter: blur(20px) saturate(1.22);
}

.status-tile--runner {
  grid-template-columns: 48px minmax(0, 0.9fr) minmax(300px, 1.1fr);
}

.status-tile__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  color: #2f63ff;
  background: rgba(79, 124, 255, 0.12);
  font-size: 22px;
}

.status-tile__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.status-tile__label {
  color: #667085;
  font-size: 12px;
  font-weight: 700;
}

.status-tile__value {
  color: #162033;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
}

.status-tile__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.status-tile__actions--compact {
  justify-self: end;
}

.runner-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.runner-command {
  font-size: 12px;
  color: #365ec8;
  word-break: break-all;
}

.sourcing-layout,
.workbench,
.detail-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workbench-top {
  display: grid;
  grid-template-columns: minmax(0, 1.18fr) minmax(420px, 0.82fr);
  gap: 16px;
  align-items: start;
}

.create-task-card,
.task-list-card {
  height: 100%;
}

.create-task-form {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-header-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header-line > :first-child {
  min-width: 0;
}

.card-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.card-header-actions .el-button + .el-button {
  margin-left: 0;
}

.task-list-actions {
  flex: 0 0 auto;
  gap: 10px 20px;
}

.task-list-actions .el-checkbox {
  margin-right: 0;
  white-space: nowrap;
}

.task-list-actions .el-button {
  min-width: 128px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.form-grid--primary {
  grid-template-columns: 1.15fr 0.85fr;
}

.form-grid--compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.platform-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.task-subtitle {
  margin-top: 4px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.metric-card {
  min-height: 86px;
  padding: 14px;
  border: 1px solid rgba(78, 92, 130, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.56);
}

.metric-label {
  display: block;
  color: #667085;
  font-size: 12px;
  margin-bottom: 8px;
}

.metric-card strong {
  font-size: 26px;
  line-height: 1;
}

.task-meta-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  gap: 16px;
}

.detail-grid--approval {
  grid-template-columns: 1.1fr 0.9fr;
}

.log-list,
.audit-list,
.outreach-list,
.drawer-stack,
.platform-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.platform-card,
.log-item,
.audit-item,
.outreach-card,
.screenshot-card {
  padding: 14px;
  border: 1px solid rgba(78, 92, 130, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.56);
}

/* 平台连接相关增强样式 */
.platform-overview {
  padding: 16px;
  border-radius: 8px;
  background: rgba(79, 124, 255, 0.06);
  border: 1px solid rgba(79, 124, 255, 0.15);
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.connected-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.connected-tag {
  font-weight: 500;
}

.section-title {
  font-weight: 700;
  font-size: 15px;
  color: #162033;
  margin-bottom: 6px;
}

.section-desc {
  margin-bottom: 12px;
  font-size: 13px;
}

.platform-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.platform-card:hover {
  border-color: rgba(79, 124, 255, 0.35);
  box-shadow: 0 4px 16px rgba(31, 50, 88, 0.08);
}

.platform-card--active {
  border-color: rgba(82, 196, 26, 0.4);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(246, 255, 237, 0.4));
}

.platform-card__head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.platform-card__icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(79, 124, 255, 0.1);
  color: #2f63ff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.platform-card__info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.platform-card__info strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.platform-card__account {
  font-size: 12px;
  padding-left: 46px;
}

.platform-card__actions {
  display: flex;
  justify-content: flex-end;
}

/* 本地连接配置 */
.local-runner-config {
  padding: 4px 0;
}

.runner-status-inline {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.5;
}

/* 平台状态卡中已连接标签 */
.connected-platform-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.platform-card__head,
.log-item__top,
.audit-item__meta,
.outreach-card__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.log-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-message {
  margin: 10px 0 6px;
  color: #162033;
  font-weight: 600;
}

.screenshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.screenshot-card {
  position: relative;
  padding: 0;
  overflow: hidden;
}

.screenshot-card--deletable:hover .screenshot-delete-btn {
  opacity: 1;
}

.screenshot-delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.45);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 2;
}

.screenshot-delete-btn:hover {
  background: rgba(234, 67, 53, 0.75);
}

.screenshot-image,
.screenshot-loading {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  background: rgba(226, 234, 252, 0.65);
}

.screenshot-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667085;
  font-size: 13px;
}

.screenshot-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
}

.screenshot-link {
  color: #365ec8;
  font-size: 12px;
  word-break: break-all;
}

.outreach-message {
  margin: 10px 0;
  color: #344054;
  white-space: pre-wrap;
  line-height: 1.7;
}

.outreach-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 1480px) {
  .control-strip,
  .workbench-top {
    grid-template-columns: 1fr;
  }

  .status-tile,
  .status-tile--runner {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .status-tile__actions,
  .status-tile__actions--compact {
    grid-column: 1 / -1;
    justify-self: stretch;
  }
}

@media (max-width: 1200px) {
  .detail-grid,
  .detail-grid--approval {
    grid-template-columns: 1fr;
  }

  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .task-meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .form-grid--compact {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .card-header-line {
    align-items: flex-start;
    flex-direction: column;
  }

  .card-header-actions {
    justify-content: flex-start;
  }

  .form-grid,
  .form-grid--primary,
  .metric-grid,
  .task-meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
