import request from './request'

export const DEFAULT_LOCAL_RUNNER_BASE = 'http://127.0.0.1:18765'

export function getSourcingPlatforms() {
  return request.get('/sourcing/platforms')
}

export function saveSourcingPlatform(data) {
  return request.post('/sourcing/platforms', data)
}

export function getSourcingTasks() {
  return request.get('/sourcing/tasks')
}

export function getSourcingTaskDetail(id) {
  return request.get(`/sourcing/tasks/${id}`)
}

export function createSourcingTask(data) {
  return request.post('/sourcing/tasks', data)
}

export function deleteSourcingTask(taskId) {
  return request.delete(`/sourcing/tasks/${taskId}`)
}

export function launchSourcingTask(id) {
  return request.post(`/sourcing/tasks/${id}/run`)
}

export function downloadLocalRunnerPackage() {
  return request.get('/sourcing/runner-package', {
    responseType: 'blob',
    silent: true
  })
}

export function reviewOutreach(taskId, outreachId, action) {
  return request.post(`/sourcing/tasks/${taskId}/outreach/${outreachId}/review`, { action })
}

export function getSourcingScreenshot(taskId, screenshotId) {
  return request.get(`/sourcing/tasks/${taskId}/screenshots/${screenshotId}/image`, {
    responseType: 'blob'
  })
}

export async function getLocalRunnerHealth(baseUrl = DEFAULT_LOCAL_RUNNER_BASE) {
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/health`)
  if (!response.ok) {
    throw new Error('本地执行器未启动')
  }
  return response.json()
}

export async function wakeLocalRunner(payload, baseUrl = DEFAULT_LOCAL_RUNNER_BASE) {
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/launch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: payload.task_id,
      backend_base_url: payload.backend_base_url,
      runner_token: payload.runner_token,
      session_id: payload.session_id
    })
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data?.detail || data?.message || '唤起本地执行器失败')
  }
  return data
}

// 日志与截图管理
export function clearTaskLogs(taskId) {
  return request.delete(`/sourcing/tasks/${taskId}/logs`)
}

export function deleteTaskLog(taskId, logId) {
  return request.delete(`/sourcing/tasks/${taskId}/logs/${logId}`)
}

export function clearTaskScreenshots(taskId) {
  return request.delete(`/sourcing/tasks/${taskId}/screenshots`)
}

export function deleteTaskScreenshot(taskId, screenshotId) {
  return request.delete(`/sourcing/tasks/${taskId}/screenshots/${screenshotId}`)
}

// 按职位维度查询（切换职位时显示该职位下所有任务的日志/截图）
export function getPositionLogs(positionId, limit = 50) {
  return request.get(`/sourcing/positions/${positionId}/logs`, { params: { limit } })
}

export function getPositionScreenshots(positionId, limit = 30) {
  return request.get(`/sourcing/positions/${positionId}/screenshots`, { params: { limit } })
}
