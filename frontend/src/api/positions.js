import request from './request'

export function getPositions(params) {
  return request.get('/positions', { params })
}

export function getPositionStats() {
  return request.get('/positions/stats/summary')
}

export function getPosition(id) {
  return request.get(`/positions/${id}`)
}

export function createPosition(data) {
  return request.post('/positions', data)
}

export function updatePosition(id, data) {
  return request.put(`/positions/${id}`, data)
}

export function deletePosition(id) {
  return request.delete(`/positions/${id}`)
}
