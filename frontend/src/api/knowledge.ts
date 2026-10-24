import http from './http'

export function listFaqs(params: Record<string, unknown> = {}) {
  return http.get('/knowledge/faqs', { params })
}

export function createFaq(data: Record<string, unknown>) {
  return http.post('/knowledge/faqs', data)
}

export function updateFaq(id: number, data: Record<string, unknown>) {
  return http.put(`/knowledge/faqs/${id}`, data)
}

export function deleteFaq(id: number) {
  return http.delete(`/knowledge/faqs/${id}`)
}

export function listDocuments(params: Record<string, unknown> = {}) {
  return http.get('/knowledge/documents', { params })
}

export function getDocument(id: number) {
  return http.get(`/knowledge/documents/${id}`)
}

export function deleteDocument(id: number) {
  return http.delete(`/knowledge/documents/${id}`)
}

export function uploadDocument(form: FormData) {
  return http.post('/knowledge/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listCategories() {
  return http.get('/knowledge/categories')
}

export function documentFileUrl(id: number) {
  return `/api/v1/knowledge/documents/${id}/file`
}
