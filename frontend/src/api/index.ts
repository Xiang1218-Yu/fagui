import axios from 'axios';
import type {
  Source, CrawlRun, Regulation, Change, Review,
  ImpactAssessment, Subscription, Notification,
  PaginatedResponse, DashboardStats, DiffResult,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const dashboardApi = {
  getStats: () => api.get<DashboardStats>('/dashboard').then(r => r.data),
};

export const sourcesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Source>>('/sources', { params }).then(r => r.data),
  get: (id: string) =>
    api.get<Source>(`/sources/${id}`).then(r => r.data),
  create: (data: Partial<Source>) =>
    api.post<Source>('/sources', data).then(r => r.data),
  update: (id: string, data: Partial<Source>) =>
    api.put<Source>(`/sources/${id}`, data).then(r => r.data),
  delete: (id: string) =>
    api.delete(`/sources/${id}`),
  pause: (id: string) =>
    api.post<Source>(`/sources/${id}/pause`).then(r => r.data),
  resume: (id: string) =>
    api.post<Source>(`/sources/${id}/resume`).then(r => r.data),
  triggerCrawl: (id: string) =>
    api.post<CrawlRun>(`/sources/${id}/crawl`).then(r => r.data),
  getCrawlRuns: (id: string, params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<CrawlRun>>(`/sources/${id}/crawl-runs`, { params }).then(r => r.data),
  triggerAllCrawls: () =>
    api.post<{ triggered: number; tasks: unknown[] }>('/sources/crawl/trigger', { triggered_by: 'manual' }).then(r => r.data),
};

export const crawlRunsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<CrawlRun>>('/crawl-runs', { params }).then(r => r.data),
  get: (id: string) =>
    api.get<CrawlRun>(`/crawl-runs/${id}`).then(r => r.data),
  getLogs: (id: string) =>
    api.get(`/crawl-runs/${id}/logs`).then(r => r.data),
};

export const regulationsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Regulation>>('/regulations', { params }).then(r => r.data),
  get: (id: string) =>
    api.get<Regulation>(`/regulations/${id}`).then(r => r.data),
  getSnapshots: (id: string, params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<unknown>>(`/regulations/${id}/snapshots`, { params }).then(r => r.data),
  getAttachments: (id: string, params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<unknown>>(`/regulations/${id}/attachments`, { params }).then(r => r.data),
  getChanges: (id: string, params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Change>>(`/regulations/${id}/changes`, { params }).then(r => r.data),
  merge: (id: string, duplicateId: string, confidence: number) =>
    api.post(`/regulations/${id}/merge?duplicate_id=${duplicateId}&confidence=${confidence}`).then(r => r.data),
};

export const changesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Change>>('/changes', { params }).then(r => r.data),
  get: (id: string) =>
    api.get<Change>(`/changes/${id}`).then(r => r.data),
  getDiff: (id: string) =>
    api.get<DiffResult>(`/changes/${id}/diff`).then(r => r.data),
  markReviewed: (id: string) =>
    api.post(`/changes/${id}/mark-reviewed`).then(r => r.data),
};

export const reviewsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Review>>('/reviews', { params }).then(r => r.data),
  get: (id: string) =>
    api.get<Review>(`/reviews/${id}`).then(r => r.data),
  getByChangeId: (changeId: string) =>
    api.get<Review>(`/reviews/by-change/${changeId}`).then(r => r.data),
  claim: (reviewId: string, reviewerId: string, reviewerName: string) =>
    api.post<Review>(`/reviews/${reviewId}/claim?reviewer_id=${reviewerId}&reviewer_name=${encodeURIComponent(reviewerName)}`).then(r => r.data),
  update: (id: string, data: Partial<Review>) =>
    api.put<Review>(`/reviews/${id}`, data).then(r => r.data),
  getStats: () =>
    api.get<Record<string, number>>('/reviews/stats/summary').then(r => r.data),
};

export const impactApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<ImpactAssessment>>('/impact-assessments', { params }).then(r => r.data),
  get: (id: string) =>
    api.get<ImpactAssessment>(`/impact-assessments/${id}`).then(r => r.data),
  create: (data: Partial<ImpactAssessment> & { change_id: string }) =>
    api.post<ImpactAssessment>('/impact-assessments', data).then(r => r.data),
  update: (id: string, data: Partial<ImpactAssessment>) =>
    api.put<ImpactAssessment>(`/impact-assessments/${id}`, data).then(r => r.data),
  submit: (id: string) =>
    api.post<ImpactAssessment>(`/impact-assessments/${id}/submit`).then(r => r.data),
};

export const subscriptionsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Subscription>>('/subscriptions', { params }).then(r => r.data),
  get: (id: string) =>
    api.get<Subscription>(`/subscriptions/${id}`).then(r => r.data),
  create: (data: Partial<Subscription>) =>
    api.post<Subscription>('/subscriptions', data).then(r => r.data),
  update: (id: string, data: Partial<Subscription>) =>
    api.put<Subscription>(`/subscriptions/${id}`, data).then(r => r.data),
  delete: (id: string) =>
    api.delete(`/subscriptions/${id}`),
};

export const notificationsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PaginatedResponse<Notification>>('/notifications', { params }).then(r => r.data),
  getUnreadCount: (userId: string) =>
    api.get<{ unread_count: number }>(`/notifications/unread-count?user_id=${userId}`).then(r => r.data),
  markRead: (id: string) =>
    api.post<Notification>(`/notifications/${id}/read`).then(r => r.data),
  markAllRead: (userId: string) =>
    api.post(`/notifications/read-all?user_id=${userId}`).then(r => r.data),
};

export default api;
