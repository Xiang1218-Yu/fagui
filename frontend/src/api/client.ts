import axios from 'axios'

export const api = axios.create({ timeout: 120000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fagui_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('fagui_token')
      localStorage.removeItem('fagui_user')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export async function downloadSnapshot(snapshotId: number, kind: 'raw' | 'text') {
  const resp = await api.get(`/api/snapshots/${snapshotId}/${kind}`, {
    responseType: kind === 'raw' ? 'blob' : 'text',
  })
  if (kind === 'text') {
    return resp.data as string
  }
  const blob = new Blob([resp.data])
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `snapshot_${snapshotId}`
  a.click()
  window.URL.revokeObjectURL(url)
  return ''
}
