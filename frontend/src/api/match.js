import request from './request'

// 单个候选人匹配
export function runMatch(candidateId, positionId) {
  return request.post('/match', { candidate_id: candidateId, position_id: positionId })
}

// 批量匹配（某职位下所有候选人）
export function batchMatch(positionId) {
  return request.post('/match/batch', { position_id: positionId })
}

// 获取某职位的匹配结果列表（按分数降序）
export function getPositionMatches(positionId) {
  return request.get(`/match/position/${positionId}`)
}
