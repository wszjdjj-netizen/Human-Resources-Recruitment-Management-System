import request from './request'

export function getAiConfig() {
  return request.get('/ai-config')
}

export function updateAiConfig(data) {
  return request.put('/ai-config', data)
}

export function testAiConnection() {
  return request.post('/ai-config/test')
}

export function activateAiConfig(id) {
  return request.post(`/ai-config/activate/${id}`)
}

export function deleteAiConfig(id) {
  return request.delete(`/ai-config/${id}`)
}
