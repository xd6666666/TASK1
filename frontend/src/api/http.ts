import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('zf_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body.code === 'number' && body.code !== 200) {
      ElMessage.error(body.msg || '请求失败')
      return Promise.reject(new Error(body.msg || '请求失败'))
    }
    return body
  },
  (err) => {
    const status = err?.response?.status
    const msg = err?.response?.data?.detail || err?.response?.data?.msg || err.message
    if (status === 401) {
      localStorage.removeItem('zf_token')
      localStorage.removeItem('zf_user')
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
    ElMessage.error(typeof msg === 'string' ? msg : '网络错误')
    return Promise.reject(err)
  },
)

export default http
