import request from './request'

// 登录
export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

// 注册
export function register(data) {
  return request.post('/auth/register', data)
}

// 获取当前用户信息
export function getMe() {
  return request.get('/auth/me')
}

// 退出登录
export function logout() {
  return request.post('/auth/logout', null, { silent: true })
}

// 更新当前用户资料
export function updateMe(data) {
  return request.post('/auth/me/update', data).catch((error) => {
    if (error?.response?.status === 404 || error?.response?.status === 405) {
      return request.put('/auth/me', data)
    }
    throw error
  })
}
