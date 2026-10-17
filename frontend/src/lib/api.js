import { useEffect, useState } from 'react'
import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const tokens = {
  get access() { return localStorage.getItem('access') },
  get refresh() { return localStorage.getItem('refresh') },
  set({ access, refresh }) {
    localStorage.setItem('access', access)
    if (refresh) localStorage.setItem('refresh', refresh)
  },
  clear() {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
  },
}

const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  if (tokens.access) config.headers.Authorization = `Bearer ${tokens.access}`
  return config
})

// One shared refresh call, so parallel 401s don't each hit /refresh.
let refreshing = null

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retried || !tokens.refresh || original.url.startsWith('/auth/')) {
      return Promise.reject(error)
    }
    original._retried = true
    try {
      refreshing ??= axios.post(`${baseURL}/auth/refresh/`, { refresh: tokens.refresh }).finally(() => { refreshing = null })
      const { data } = await refreshing
      tokens.set(data)
      return api(original)
    } catch {
      tokens.clear()
      window.location.assign('/login')
      return Promise.reject(error)
    }
  },
)

export function errorMessage(error) {
  const data = error.response?.data
  if (!data) return 'Network error. Is the API running?'
  return data.detail || Object.values(data).flat().join(' ') || 'Something went wrong.'
}

export default api

export function useApi(url) {
  const [version, setVersion] = useState(0)
  const key = `${url}#${version}`
  const [state, setState] = useState({ key: null, data: null, error: null })

  useEffect(() => {
    let active = true
    api.get(url)
      .then((res) => active && setState({ key, data: res.data, error: null }))
      .catch((error) => active && setState({ key, data: null, error: errorMessage(error) }))
    return () => { active = false }
  }, [url, key])

  // Loading until the response for the current url (and reload) arrives, so filter changes show loaders too.
  return { data: state.data, error: state.error, loading: state.key !== key, reload: () => setVersion((v) => v + 1) }
}
