const HTML_ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPE_MAP[char])
}

export function renderSafeMarkdown(text, options = {}) {
  if (!text) return '<p class="text-muted">暂无分析内容</p>'

  let cleaned = String(text)
  if (options.stripMatchMarkers) {
    cleaned = cleaned
      .replace(/\[DIM_SCORES\].*?\[\/DIM_SCORES\]\s*/gs, '')
      .replace(/\[HAS_RELEVANT_EXP\](true|false)\[\/HAS_RELEVANT_EXP\]\s*/g, '')
  }

  let html = escapeHtml(cleaned)
    .replace(/^### (.*?)(?=\n|$)/gm, '<h4>$1</h4>')
    .replace(/^## (.*?)(?=\n|$)/gm, '<h3>$1</h3>')
    .replace(/^#{4,6} (.*?)(?=\n|$)/gm, '<h4>$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^- (.*?)(?=\n|$)/gm, '<li>$1</li>')
    .replace(/^\d+\. (.*?)(?=\n|$)/gm, '<li>$1</li>')
    .replace(/\n\n+/g, '</p><p>')
    .replace(/\n/g, '<br/>')

  return '<p>' + html + '</p>'
}
