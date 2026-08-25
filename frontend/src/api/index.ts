import axios from 'axios'
import type {
  ChangeEvent,
  CrawlRun,
  DashboardStats,
  Document,
  Notification,
  Regulation,
  ReviewItem,
  Snapshot,
  Source,
  Subscription,
} from '../types'

const client = axios.create({ baseURL: '/api' })

const TOKEN_KEY = 'fagui_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

// attach bearer token to every request
client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// on 401, drop the token and bounce to login
client.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken()
      if (location.pathname !== '/login') location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ---------- Auth ----------
export interface AuthUser {
  username: string
  display_name: string
  role: string
}
export const login = async (username: string, password: string): Promise<AuthUser> => {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)
  const { data } = await client.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  setToken(data.access_token)
  return { username: data.username, display_name: data.display_name, role: data.role }
}
export const fetchMe = () => client.get<AuthUser>('/auth/me').then((r) => r.data)
export const testEmail = (to: string) =>
  client.post('/subscriptions/test-email', { to }).then((r) => r.data)

// ---------- Sources ----------
export const listSources = () => client.get<Source[]>('/sources').then((r) => r.data)
export const createSource = (data: Partial<Source>) =>
  client.post<Source>('/sources', data).then((r) => r.data)
export const updateSource = (id: number, data: Partial<Source>) =>
  client.put<Source>(`/sources/${id}`, data).then((r) => r.data)
export const deleteSource = (id: number) => client.delete(`/sources/${id}`)
export const crawlSource = (id: number) =>
  client.post<CrawlRun>(`/sources/${id}/crawl`).then((r) => r.data)

// ---------- Runs ----------
export const listRuns = (sourceId?: number) =>
  client
    .get<CrawlRun[]>('/runs', { params: sourceId ? { source_id: sourceId } : {} })
    .then((r) => r.data)
export const runSnapshots = (runId: number) =>
  client.get<Snapshot[]>(`/runs/${runId}/snapshots`).then((r) => r.data)

// ---------- Changes ----------
export const listChanges = (params?: { document_id?: number; change_type?: string }) =>
  client.get<ChangeEvent[]>('/changes', { params }).then((r) => r.data)
export const getChange = (id: number) =>
  client.get<ChangeEvent>(`/changes/${id}`).then((r) => r.data)
export const changeSnapshots = (id: number) =>
  client
    .get<{
      old: Snapshot | null
      new: Snapshot | null
      old_text: string
      new_text: string
      diff_text: string
    }>(`/changes/${id}/snapshots`)
    .then((r) => r.data)

// ---------- Reviews ----------
export const listReviews = (status?: string) =>
  client.get<ReviewItem[]>('/reviews', { params: status ? { status } : {} }).then((r) => r.data)
export const assignReview = (id: number, assignee: string) =>
  client.post<ReviewItem>(`/reviews/${id}/assign`, { assignee }).then((r) => r.data)
export const decideReview = (
  id: number,
  data: {
    status: string
    impact_level: string
    decision_note: string
    impact_note: string
    affected_business: string
    reviewed_by: string
  },
) => client.post<ReviewItem>(`/reviews/${id}/decide`, data).then((r) => r.data)

// ---------- Regulations / Documents ----------
export const listRegulations = () =>
  client.get<Regulation[]>('/regulations').then((r) => r.data)
export const regulationDocuments = (id: number) =>
  client.get<Document[]>(`/regulations/${id}/documents`).then((r) => r.data)
export const listDocuments = (sourceId?: number) =>
  client
    .get<Document[]>('/documents', { params: sourceId ? { source_id: sourceId } : {} })
    .then((r) => r.data)

// ---------- Subscriptions / Notifications ----------
export const listSubscriptions = () =>
  client.get<Subscription[]>('/subscriptions').then((r) => r.data)
export const createSubscription = (data: Partial<Subscription>) =>
  client.post<Subscription>('/subscriptions', data).then((r) => r.data)
export const deleteSubscription = (id: number) => client.delete(`/subscriptions/${id}`)
export const listNotifications = (unreadOnly = false) =>
  client
    .get<Notification[]>('/notifications', { params: { unread_only: unreadOnly } })
    .then((r) => r.data)
export const markNotificationRead = (id: number) =>
  client.post<Notification>(`/notifications/${id}/read`).then((r) => r.data)
export const markAllRead = () => client.post('/notifications/read-all').then((r) => r.data)

// ---------- Dashboard ----------
export const getStats = () => client.get<DashboardStats>('/dashboard/stats').then((r) => r.data)
