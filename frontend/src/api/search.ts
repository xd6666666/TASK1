import http from './http'

export function searchQuery(data: {
  query: string
  mode?: string
  threshold?: number
  top_k?: number
  feedback?: string
}) {
  return http.post('/search/query', data)
}
