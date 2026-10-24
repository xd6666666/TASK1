import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, register as registerApi } from '@/api/auth'

export type UserInfo = {
  id: number
  username: string
  nickname: string
  role: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('zf_token') || '')
  const user = ref<UserInfo | null>(
    localStorage.getItem('zf_user') ? JSON.parse(localStorage.getItem('zf_user')!) : null,
  )

  async function login(username: string, password: string) {
    const res: any = await loginApi(username, password)
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('zf_token', token.value)
    localStorage.setItem('zf_user', JSON.stringify(user.value))
  }

  async function register(username: string, password: string, nickname: string) {
    const res: any = await registerApi(username, password, nickname)
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('zf_token', token.value)
    localStorage.setItem('zf_user', JSON.stringify(user.value))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('zf_token')
    localStorage.removeItem('zf_user')
  }

  return { token, user, login, register, logout }
})
