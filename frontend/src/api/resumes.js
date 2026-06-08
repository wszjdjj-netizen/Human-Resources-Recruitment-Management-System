import request from './request'

// 批量上传简历文件
export function uploadResumes(formData, positionId) {
  return request.post(`/resumes/upload?position_id=${positionId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// AI解析简历
export function parseResume(candidateId) {
  return request.post(`/resumes/${candidateId}/parse`)
}

// 获取解析后的简历详情
export function getResumeDetail(candidateId) {
  return request.get(`/resumes/${candidateId}`)
}
