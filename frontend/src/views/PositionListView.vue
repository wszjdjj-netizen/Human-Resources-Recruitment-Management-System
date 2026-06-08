<template>
  <div class="page-container">
    <div class="page-header page-hero">
      <div>
        <span class="eyebrow">Hiring Command</span>
        <h2>职位管理</h2>
        <p class="text-muted">集中管理岗位、上传简历并追踪候选人匹配结果。</p>
      </div>
      <div class="hero-actions">
        <el-button type="success" @click="jdDialogRef?.open()">
          <el-icon><MagicStick /></el-icon> 从JD智能创建
        </el-button>
        <el-button type="primary" @click="$router.push('/positions/create')">
          <el-icon><Plus /></el-icon> 手动创建职位
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <el-card class="glass-card filter-card" style="margin-bottom: 16px;">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="8" :lg="6">
          <el-input v-model="filters.search" placeholder="搜索职位名称" clearable @clear="fetchPositions" @keyup.enter="fetchPositions" />
        </el-col>
        <el-col :xs="24" :sm="6" :lg="4">
          <el-select v-model="filters.status" placeholder="状态筛选" clearable @change="fetchPositions">
            <el-option label="开放" value="开放" />
            <el-option label="关闭" value="关闭" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="4" :lg="3">
          <el-button type="primary" @click="fetchPositions">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 职位列表 -->
    <el-card class="glass-card">
      <el-table :data="positions" stripe v-loading="loading" empty-text="暂无职位，点击右上角发布" class="responsive-table">
        <el-table-column prop="title" label="职位名称" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/positions/${row.id}`)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" min-width="110" />
        <el-table-column prop="location" label="工作地点" min-width="110" />
        <el-table-column prop="salary_range" label="薪资范围" min-width="120" />
        <el-table-column prop="status" label="状态" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === '开放' ? 'success' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="发布时间" min-width="120">
          <template #default="{ row }">
            {{ row.created_at?.split('T')[0] || '' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="210">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" @click="$router.push(`/positions/${row.id}`)">详情</el-button>
              <el-button size="small" @click="$router.push(`/positions/${row.id}/edit`)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- JD智能解析弹窗 -->
    <JDParseDialog ref="jdDialogRef" @created="fetchPositions" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { getPositions, deletePosition } from '../api/positions'
import JDParseDialog from '../components/position/JDParseDialog.vue'

const positions = ref([])
const loading = ref(false)
const jdDialogRef = ref(null)
const filters = reactive({
  search: '',
  status: ''
})

async function fetchPositions() {
  loading.value = true
  try {
    const params = {}
    if (filters.search) params.search = filters.search
    if (filters.status) params.status = filters.status
    positions.value = await getPositions(params)
  } catch {
    positions.value = []
  } finally {
    loading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除职位「${row.title}」吗？此操作不可恢复。`, '删除确认', {
      type: 'warning'
    })
    await deletePosition(row.id)
    await fetchPositions()
  } catch {
    // 取消删除
  }
}

onMounted(() => fetchPositions())
</script>
