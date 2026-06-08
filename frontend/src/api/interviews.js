import request from './request'

// 列表（多 HR 共享：服务端不过滤 user_id）
export function listInterviews(params) {
  return request.get('/interviews', { params })
}

// 候选人维度历史面试
export function listCandidateInterviews(candidateId) {
  return request.get(`/candidates/${candidateId}/interviews`)
}

// 详情
export function getInterview(id) {
  return request.get(`/interviews/${id}`)
}

// 新建
export function createInterview(data) {
  return request.post('/interviews', data)
}

// 编辑
export function updateInterview(id, data) {
  return request.put(`/interviews/${id}`, data)
}

// 删除
export function deleteInterview(id) {
  return request.delete(`/interviews/${id}`)
}

// 开始面试
export function startInterview(id) {
  return request.post(`/interviews/${id}/start`)
}

// 结束面试（保存转写）
export function endInterview(id, transcript) {
  return request.post(`/interviews/${id}/end`, { transcript })
}

// 生成 AI 总结
export function summarizeInterview(id, payload = {}) {
  return request.post(`/interviews/${id}/summarize`, payload)
}

// 协作笔记追加
export function appendNotes(id, notes) {
  return request.patch(`/interviews/${id}/notes`, { notes })
}

// 平台枚举
export function getInterviewPlatforms() {
  return request.get('/interviews/platforms')
}

// 演示用 mock 剧本
export function getMockScript(id) {
  return request.get(`/interviews/${id}/script`)
}
