<template>
  <div>
    <el-alert
      v-if="error"
      type="error"
      :title="`页面渲染失败：${error.message}`"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    >
      <template #default>
        <pre style="white-space: pre-wrap; word-break: break-all; max-height: 240px; overflow: auto; background: #fff5f5; padding: 10px; border-radius: 6px; font-size: 12px;">{{ errorStack }}</pre>
        <el-button type="primary" size="small" @click="reload" style="margin-top: 8px;">重新加载页面</el-button>
        <el-button size="small" @click="reset">重置组件状态</el-button>
      </template>
    </el-alert>
    <slot v-if="!error" />
    <slot v-else name="fallback">
      <div style="padding: 24px; text-align: center; color: #909399;">
        该页面暂时无法渲染，请尝试刷新或联系管理员。
      </div>
    </slot>
  </div>
</template>

<script setup>
import { onErrorCaptured, ref } from 'vue'

const props = defineProps({
  /** 是否在捕获错误后阻止上层继续渲染 */
  stop: { type: Boolean, default: true },
})

const error = ref(null)
const errorStack = ref('')

onErrorCaptured((err, instance, info) => {
  console.error('[ErrorBoundary 捕获错误]', err, info)
  error.value = err
  errorStack.value = (err && err.stack) ? err.stack : String(err)
  // 阻止错误继续向上冒泡到父组件
  return !props.stop
})

function reset() {
  error.value = null
  errorStack.value = ''
}

function reload() {
  window.location.reload()
}
</script>
