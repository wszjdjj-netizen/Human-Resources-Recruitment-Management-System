<template>
  <div class="page-container">
    <div class="page-header page-hero">
      <div>
        <span class="eyebrow">Recruiting Overview</span>
        <h2>首页概览</h2>
        <p class="text-muted">查看职位、候选人和招聘进展的实时概览。</p>
      </div>
    </div>

    <el-row :gutter="20" class="stat-grid">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="stat-card glass-card">
          <div class="stat-icon blue">
            <el-icon :size="28"><Briefcase /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.open_position_count }}</div>
            <div class="stat-label">开放职位</div>
            <div class="stat-sub">职位总数 {{ stats.position_count }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="stat-card glass-card">
          <div class="stat-icon green">
            <el-icon :size="28"><UserFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.candidate_count }}</div>
            <div class="stat-label">候选人总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="stat-card glass-card">
          <div class="stat-icon amber">
            <el-icon :size="28"><ChatLineSquare /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.contacted_count }}</div>
            <div class="stat-label">待联系/面试中</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="stat-card glass-card">
          <div class="stat-icon violet">
            <el-icon :size="28"><TrophyBase /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.passed_count }}</div>
            <div class="stat-label">已通过</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :lg="12">
        <el-card class="glass-card">
          <template #header>
            <div class="flex-between">
              <span><strong>各职位候选人分布</strong></span>
              <el-tag size="small" effect="plain">含开放/关闭</el-tag>
            </div>
          </template>
          <el-table :data="stats.position_distribution || []" size="small" empty-text="暂无数据">
            <el-table-column prop="title" label="职位" />
            <el-table-column prop="status" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === '开放' ? 'success' : 'info'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="候选人数" width="100" align="center" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card class="glass-card">
          <template #header>
            <div class="flex-between">
              <span><strong>快速入口</strong></span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/positions/create')">发布新职位</el-button>
            <el-button @click="$router.push('/positions')">管理职位</el-button>
            <el-button @click="$router.push('/talent-pool')">查看人才池</el-button>
            <el-button @click="$router.push('/ai-config')">AI配置</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Briefcase, ChatLineSquare, TrophyBase, UserFilled } from '@element-plus/icons-vue'
import { getPositions, getPositionStats } from '../api/positions'

const stats = ref({
  position_count: 0,
  open_position_count: 0,
  candidate_count: 0,
  contacted_count: 0,
  passed_count: 0,
  position_distribution: []
})

function isOpenStatus(status) {
  return String(status || '').trim() === '开放'
}

function applyPositionFallback(positions) {
  stats.value.position_count = positions.length
  stats.value.open_position_count = positions.filter((item) => isOpenStatus(item.status)).length

  if (!stats.value.position_distribution.length) {
    stats.value.position_distribution = positions.map((item) => ({
      title: item.title,
      status: item.status || '开放',
      count: item.candidate_count || 0
    }))
  }
}

async function fetchStats() {
  let summary = null
  try {
    summary = await getPositionStats()
    stats.value.position_count = summary?.position_count ?? 0
    stats.value.open_position_count = summary?.open_position_count ?? 0
    stats.value.candidate_count = summary?.candidate_count ?? 0
    stats.value.contacted_count = summary?.contacted_count ?? 0
    stats.value.passed_count = summary?.passed_count ?? 0
    stats.value.position_distribution = summary?.position_distribution || []
  } catch {
    summary = null
  }

  try {
    const positions = await getPositions()
    const statsLooksEmpty = !summary || (stats.value.position_count === 0 && positions.length > 0)
    if (statsLooksEmpty || positions.length !== stats.value.position_count) {
      applyPositionFallback(positions)
    }
  } catch {
    // Keep the summary result if the fallback list request fails.
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.stat-card {
  cursor: default;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 24px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: white;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.46), 0 12px 28px rgba(44, 62, 98, 0.12);
}

.stat-icon.blue { background: linear-gradient(135deg, #4f7cff, #12b6cb); }
.stat-icon.green { background: linear-gradient(135deg, #19b879, #12b6cb); }
.stat-icon.amber { background: linear-gradient(135deg, #f5a524, #ef476f); }
.stat-icon.violet { background: linear-gradient(135deg, #8b5cf6, #4f7cff); }

.stat-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 76px;
}

.stat-value {
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #172033;
  line-height: 1.1;
}

.stat-label {
  font-size: 13px;
  color: #667085;
  margin-top: 6px;
  font-weight: 500;
}

.stat-sub {
  margin-top: 6px;
  color: #2f63ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}
</style>
