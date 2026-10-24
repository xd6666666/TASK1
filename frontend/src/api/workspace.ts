import http from './http'

export function listConversations(params: Record<string, string> = {}) {
  return http.get('/workspace/conversations', { params })
}

export function getConversation(id: number) {
  return http.get(`/workspace/conversations/${id}`)
}

export function aiSuggest(id: number) {
  return http.get(`/workspace/conversations/${id}/ai-suggest`)
}

export function sendMessage(id: number, content: string, fromAi = false) {
  return http.post(`/workspace/conversations/${id}/messages`, {
    content,
    from_ai: fromAi,
  })
}

export function closeConversation(id: number) {
  return http.post(`/workspace/conversations/${id}/close`)
}
