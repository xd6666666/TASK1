import http from './http'

export function fetchSettings() {
  return http.get('/settings')
}

export function saveSettings(data: Record<string, unknown>) {
  return http.put('/settings', data)
}

export function modelHealth() {
  return http.get('/settings/model/health')
}
