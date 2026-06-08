<template>
  <el-dialog
    v-model="visible"
    title="智能JD解析 - 自动创建职位"
    width="700px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <!-- 输入方式选择 -->
    <el-tabs v-model="inputMode">
      <el-tab-pane label="粘贴JD文本" name="text">
        <el-input
          v-model="jdText"
          type="textarea"
          :rows="10"
          placeholder="请直接粘贴从招聘平台复制的JD文本内容...&#10;&#10;例如：&#10;岗位名称：高级Python工程师&#10;部门：技术部&#10;工作地点：北京&#10;薪资：25K-40K&#10;岗位职责：...&#10;任职要求：..."
        />
      </el-tab-pane>
      <el-tab-pane label="粘贴职位链接" name="url">
        <el-input
          v-model="jdUrl"
          placeholder="请粘贴招聘平台的职位链接，如：https://www.zhipin.com/job_detail/xxx.html"
        />
        <div class="text-muted" style="margin-top: 6px;">
          支持：Boss直聘、猎聘、领英、智联等招聘平台的公开职位链接
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 解析按钮 -->
    <div style="text-align: center; margin: 16px 0;">
      <el-button
        type="primary"
        size="large"
        :loading="parsing"
        :disabled="!hasInput"
        @click="handleParse"
      >
        <el-icon><MagicStick /></el-icon> 开始AI解析
      </el-button>
    </div>

    <!-- 解析结果 -->
    <div v-if="parseResult" v-loading="parsing">
      <el-divider />
      <h4 style="margin-bottom: 12px;">解析结果预览</h4>
      <el-form :model="parseResult" label-width="90px" size="default">
        <el-form-item label="职位名称">
          <el-input v-model="parseResult.title" />
        </el-form-item>
        <el-form-item label="所属部门">
          <el-input v-model="parseResult.department" />
        </el-form-item>
        <el-form-item label="工作地点">
          <el-input v-model="parseResult.location" />
        </el-form-item>
        <el-form-item label="薪资范围">
          <el-input v-model="parseResult.salary_range" />
        </el-form-item>
        <el-form-item label="岗位JD">
          <el-input v-model="parseResult.job_description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="任职要求">
          <el-input v-model="parseResult.requirements" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>

      <div style="text-align: center; margin-top: 12px;">
        <el-button type="success" :loading="creating" @click="handleCreate">
          确认并创建职位
        </el-button>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../api/request'
import { createPosition } from '../../api/positions'

const emit = defineEmits(['created'])

const visible = ref(false)
const inputMode = ref('text')
const jdText = ref('')
const jdUrl = ref('')
const parsing = ref(false)
const creating = ref(false)
const parseResult = ref(null)

const hasInput = computed(() => {
  return inputMode.value === 'text'
    ? jdText.value.trim().length > 20
    : jdUrl.value.trim().length > 10
})

function open() {
  visible.value = true
  jdText.value = ''
  jdUrl.value = ''
  parseResult.value = null
}

async function handleParse() {
  parsing.value = true
  parseResult.value = null
  try {
    const payload = {}
    if (inputMode.value === 'text') {
      payload.text = jdText.value.trim()
    } else {
      payload.url = jdUrl.value.trim()
    }
    const result = await request.post('/positions/parse-jd', payload)
    parseResult.value = result
    ElMessage.success('解析成功！请确认信息后创建职位')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '解析失败，请检查输入内容')
  } finally {
    parsing.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    await createPosition({
      ...parseResult.value,
      status: '开放',
      platform_name: inputMode.value === 'url' ? '外部平台' : undefined,
      platform_url: inputMode.value === 'url' ? jdUrl.value.trim() : undefined
    })
    ElMessage.success('职位创建成功！')
    visible.value = false
    emit('created')
  } catch {
    // 错误已在拦截器处理
  } finally {
    creating.value = false
  }
}

defineExpose({ open })
</script>
