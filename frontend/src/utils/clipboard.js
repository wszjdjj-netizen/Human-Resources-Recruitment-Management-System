import { ElMessage } from 'element-plus'

export async function copyText(text, label = '内容') {
  const value = (text || '').trim()
  if (!value) {
    ElMessage.warning(`暂无可复制的${label}`)
    return
  }

  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success(`${label}已复制`)
  } catch {
    const input = document.createElement('textarea')
    input.value = value
    input.style.position = 'fixed'
    input.style.opacity = '0'
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    ElMessage.success(`${label}已复制`)
  }
}
