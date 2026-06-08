<template>
  <div class="page-container">
    <div class="page-header page-hero">
      <div>
        <span class="eyebrow">Position Builder</span>
        <h2>{{ isEdit ? '编辑职位' : '发布新职位' }}</h2>
        <p class="text-muted">完善岗位画像，后续 AI 会基于这些信息完成候选人解析和匹配。</p>
      </div>
    </div>

    <el-card class="glass-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="max-width: 800px;">
        <el-form-item label="职位名称" prop="title">
          <el-input v-model="form.title" placeholder="如：高级Python工程师" />
        </el-form-item>
        <el-form-item label="所属部门" prop="department">
          <el-input v-model="form.department" placeholder="如：技术部" />
        </el-form-item>
        <el-form-item label="工作地点" prop="location">
          <el-input v-model="form.location" placeholder="如：北京" />
        </el-form-item>
        <el-form-item label="薪资范围">
          <el-input v-model="form.salary_range" placeholder="如：25K-40K" />
        </el-form-item>
        <el-form-item label="招聘人数">
          <el-input-number v-model="form.headcount" :min="1" placeholder="1" />
        </el-form-item>
        <el-form-item label="岗位JD" prop="job_description">
          <el-input
            v-model="form.job_description"
            type="textarea"
            :rows="8"
            placeholder="请输入完整的岗位描述（JD），将用于AI匹配打分..."
          />
        </el-form-item>
        <el-form-item label="任职要求">
          <el-input
            v-model="form.requirements"
            type="textarea"
            :rows="4"
            placeholder="可填写结构化的任职要求，如：1. 本科及以上学历 2. 3年以上Python经验..."
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="开放">开放</el-radio>
            <el-radio value="关闭">关闭</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-divider content-position="left">高级设置</el-divider>

        <el-form-item label="外部平台">
          <el-row :gutter="8">
            <el-col :span="8">
              <el-select v-model="form.platform_name" placeholder="选择平台" clearable>
                <el-option label="Boss直聘" value="boss" />
                <el-option label="猎聘" value="猎聘" />
                <el-option label="领英" value="领英" />
                <el-option label="智联招聘" value="智联" />
                <el-option label="前程无忧" value="51job" />
              </el-select>
            </el-col>
            <el-col :span="16">
              <el-input v-model="form.platform_url" placeholder="外部平台的职位链接（选填）" />
            </el-col>
          </el-row>
        </el-form-item>

        <el-form-item label="AI解析提示词">
          <el-input
            v-model="form.parsing_extra_prompt"
            type="textarea"
            :rows="4"
            placeholder="设置该岗位的候选人画像/额外解析要求，AI解析简历时会重点关注。&#10;&#10;例如：&#10;- 重点关注是否有大模型或AIGC相关项目经验&#10;- 候选人应具备团队管理经验（带过3人以上团队）&#10;- 优先识别是否有B端SaaS产品经验&#10;&#10;留空则使用通用解析模式。"
          />
          <div class="text-muted" style="margin-top: 4px;">
            留空使用通用解析；填写后AI解析简历时会重点识别你关注的候选人特征
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '发布职位' }}
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createPosition, updatePosition, getPosition } from '../api/positions'

const route = useRoute()
const router = useRouter()

const isEdit = ref(false)
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  title: '',
  department: '',
  location: '',
  salary_range: '',
  headcount: 1,
  job_description: '',
  requirements: '',
  status: '开放',
  parsing_extra_prompt: '',
  platform_url: '',
  platform_name: ''
})

const rules = {
  title: [{ required: true, message: '请输入职位名称', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属部门', trigger: 'blur' }],
  location: [{ required: true, message: '请输入工作地点', trigger: 'blur' }],
  job_description: [{ required: true, message: '请输入岗位JD', trigger: 'blur' }]
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    if (isEdit.value) {
      await updatePosition(route.params.id, form)
    } else {
      await createPosition(form)
    }
    router.push('/positions')
  } catch {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const id = route.params.id
  if (id && route.path.includes('edit')) {
    isEdit.value = true
    loading.value = true
    try {
      const pos = await getPosition(id)
      Object.assign(form, {
        title: pos.title,
        department: pos.department,
        location: pos.location,
        salary_range: pos.salary_range || '',
        headcount: pos.headcount || 1,
        job_description: pos.job_description,
        requirements: pos.requirements || '',
        status: pos.status,
        parsing_extra_prompt: pos.parsing_extra_prompt || '',
        platform_url: pos.platform_url || '',
        platform_name: pos.platform_name || ''
      })
    } catch {
      router.push('/positions')
    } finally {
      loading.value = false
    }
  }
})
</script>
