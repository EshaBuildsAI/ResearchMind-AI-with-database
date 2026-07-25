import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({ baseURL: BASE_URL })

function getTokens() {
  return {
    access: localStorage.getItem('rm_access_token'),
    refresh: localStorage.getItem('rm_refresh_token'),
  }
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem('rm_access_token', access_token)
  if (refresh_token) localStorage.setItem('rm_refresh_token', refresh_token)
}

export function clearTokens() {
  localStorage.removeItem('rm_access_token')
  localStorage.removeItem('rm_refresh_token')
  localStorage.removeItem('rm_user')
}

client.interceptors.request.use((config) => {
  const { access } = getTokens()
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

let refreshingPromise = null

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const { refresh } = getTokens()
      if (!refresh) {
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(error)
      }
      try {
        if (!refreshingPromise) {
          refreshingPromise = axios
            .post(`${BASE_URL}/auth/refresh`, { refresh_token: refresh })
            .finally(() => {
              refreshingPromise = null
            })
        }
        const { data } = await refreshingPromise
        setTokens(data)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return client(original)
      } catch (refreshError) {
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default client
