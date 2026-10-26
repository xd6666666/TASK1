import http from './http'

export function fetchQaOverview() {
  return http.get('/qa/overview')
}

export function listRules() {
  return http.get('/qa/rules')
}

export function createRule(data: Record<string, unknown>) {
  return http.post('/qa/rules', data)
}

export function updateRule(id: number, data: Record<string, unknown>) {
  return http.put(`/qa/rules/${id}`, data)
}

export function deleteRule(id: number) {
  return http.delete(`/qa/rules/${id}`)
}

export function listReviews() {
  return http.get('/qa/reviews')
}

export function reviewResult(id: number, pass_ok: boolean, note = '') {
  return http.post(`/qa/reviews/${id}`, { pass_ok, note })
}

export function runInspect(conversationId?: number) {
  return http.post('/qa/inspect', null, {
    params: conversationId ? { conversation_id: conversationId } : {},
  })
}
