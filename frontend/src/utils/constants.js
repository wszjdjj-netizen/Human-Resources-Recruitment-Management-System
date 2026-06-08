// 候选人状态选项
export const CANDIDATE_STATUS = {
  pending: '待联系',
  contacted: '已联系',
  interviewing: '面试中',
  passed: '已通过',
  rejected: '已淘汰'
}

// 状态列表（用于筛选下拉框）
export const CANDIDATE_STATUS_LIST = [
  { value: '待联系', label: '待联系' },
  { value: '已联系', label: '已联系' },
  { value: '面试中', label: '面试中' },
  { value: '已通过', label: '已通过' },
  { value: '已淘汰', label: '已淘汰' }
]

// 状态颜色映射
export const STATUS_COLORS = {
  '待联系': 'info',
  '已联系': 'warning',
  '面试中': 'primary',
  '已通过': 'success',
  '已淘汰': 'danger'
}

// 匹配分数颜色等级
export function getScoreColor(score) {
  if (score >= 80) return '#67c23a'  // 绿色 - 高度匹配
  if (score >= 60) return '#409eff'  // 蓝色 - 较好匹配
  if (score >= 40) return '#e6a23c'  // 橙色 - 一般匹配
  return '#f56c6c'                   // 红色 - 不匹配
}

// 匹配分数等级文字
export function getScoreLevel(score) {
  if (score >= 80) return '高度匹配'
  if (score >= 60) return '较好匹配'
  if (score >= 40) return '一般匹配'
  return '匹配度低'
}

// 职位状态
export const POSITION_STATUS_LIST = [
  { value: '开放', label: '开放' },
  { value: '关闭', label: '关闭' }
]

// 候选人来源
export const CANDIDATE_SOURCE = {
  apply: '主动投递',
  search: '平台搜寻',
  import: '手动导入'
}

export const SOURCING_STATUS_COLORS = {
  '待运行': 'info',
  '待登录': 'warning',
  '待验证码': 'warning',
  '待确认发送': 'primary',
  '运行中': 'success',
  '完成': 'success',
  '失败': 'danger'
}

export const LOG_LEVEL_COLORS = {
  info: '',
  warning: 'warning',
  error: 'danger'
}

// 面试状态
export const INTERVIEW_STATUS_LIST = [
  { value: '已预约', label: '已预约' },
  { value: '进行中', label: '进行中' },
  { value: '转写中', label: '转写中' },
  { value: '已总结', label: '已总结' },
  { value: '已取消', label: '已取消' }
]

export const INTERVIEW_STATUS_COLORS = {
  '已预约': 'info',
  '进行中': 'warning',
  '转写中': 'primary',
  '已总结': 'success',
  '已取消': 'danger'
}

// 面试推荐结论
export const RECOMMENDATION_COLORS = {
  '强烈推荐': 'success',
  '推荐': 'success',
  '待定': 'warning',
  '不推荐': 'danger'
}
