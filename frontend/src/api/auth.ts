import http from './http'

export function login(username: string, password: string) {
  return http.post('/auth/login', { username, password })
}

export function register(username: string, password: string, nickname: string) {
  return http.post('/auth/register', { username, password, nickname })
}

export function fetchMe() {
  return http.get('/auth/me')
}
