import request from './request'

// ==================== 角色管理 API ====================

/**
 * 获取所有角色（内置 + 自定义）
 * 返回 { builtin_count, custom_count, roles: [...] }
 */
export function getWorkflowRoles() {
  return request.get('/workflow/roles')
}

/**
 * 获取角色详情（内置或自定义）
 * identifier: "builtin_recruiter" 或 "123" (自定义ID)
 */
export function getWorkflowRoleDetail(identifier) {
  return request.get(`/workflow/roles/${identifier}`)
}

// ---- 自定义角色 CRUD ----

/** 新建自定义角色 */
export function createCustomRole(data) {
  return request.post('/workflow/roles/custom', data)
}

/** 修改自定义角色 */
export function updateCustomRole(roleId, data) {
  return request.put(`/workflow/roles/custom/${roleId}`, data)
}

/** 删除自定义角色 */
export function deleteCustomRole(roleId) {
  return request.delete(`/workflow/roles/custom/${roleId}`)
}

/** 调整排序 */
export function reorderCustomRoles(roleIds) {
  return request.put('/workflow/roles/custom/reorder', roleIds)
}

// ==================== 工作流匹配 API（独立于平台搜人） ====================

/** 工作流模式批量匹配 - 指定候选人列表 */
export function workflowMatch(data) {
  return request.post('/workflow/match', data)
}

/** 工作流模式全量匹配 - 职位下所有候选人 */
export function workflowMatchAll(data) {
  return request.post('/workflow/match/all', data)
}
