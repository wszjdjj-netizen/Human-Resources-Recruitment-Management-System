import request from './request'

export function getCandidates(params) {
  return request.get('/candidates', { params })
}

export function getCandidate(id) {
  return request.get(`/candidates/${id}`)
}

export function updateCandidate(id, data) {
  return request.put(`/candidates/${id}`, data)
}

export function deleteCandidate(id) {
  return request.delete(`/candidates/${id}`)
}

export function batchDeleteCandidates(ids) {
  return request.post('/candidates/batch-delete', { ids })
}
