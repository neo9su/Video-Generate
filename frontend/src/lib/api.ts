import axios, { AxiosInstance, AxiosProgressEvent } from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://10.190.0.222:8000/api/v1'

let authToken: string | null = null

if (typeof window !== 'undefined') {
  authToken = localStorage.getItem('auth_token')
}

export function setAuthToken(token: string | null) {
  authToken = token
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('auth_token', token)
    } else {
      localStorage.removeItem('auth_token')
    }
  }
}

export function getAuthToken(): string | null {
  return authToken
}

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      setAuthToken(null)
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// ─── Health ────────────────────────────────────────────────────────────
export async function healthCheck() {
  const { data } = await api.get('/health')
  return data
}

// ─── Auth ──────────────────────────────────────────────────────────────
export interface UserProfile {
  id: number
  email: string
  name: string
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserProfile
}

export async function login(email: string, password: string) {
  const { data } = await api.post<AuthResponse>('/auth/login', { email, password })
  if (data.access_token) {
    setAuthToken(data.access_token)
  }
  return data
}

export async function register(email: string, password: string, name?: string) {
  const { data } = await api.post<AuthResponse>('/auth/register', { email, password, name })
  if (data.access_token) {
    setAuthToken(data.access_token)
  }
  return data
}

export async function getProfile() {
  const { data } = await api.get<UserProfile>('/auth/me')
  return data
}

export async function updateProfile(name?: string, email?: string) {
  const { data } = await api.put<UserProfile>('/auth/me', { name, email })
  return data
}

// ─── Tasks ─────────────────────────────────────────────────────────────
export interface CreateTaskPayload {
  title?: string
  description?: string
  product_description?: string
  platform?: string
  style?: string
  language?: string
  video_length?: number
  model?: string
  image_urls?: string[]
  voice_id?: string
  prompt_id?: string
  highlight_style?: string
  reference_analysis_id?: string
  settings?: Record<string, unknown>
}

export interface Task {
  id: string
  title: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  platform?: string
  style?: string
  language?: string
  video_length?: number
  model?: string
  product_description?: string
  image_urls?: string[]
  video_url?: string
  thumbnail_url?: string
  error_message?: string
  created_at: string
  updated_at: string
}

export interface TasksQueryParams {
  page?: number
  limit?: number
  status?: string
  sort?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
}

export async function createTask(data: CreateTaskPayload) {
  const { data: response } = await api.post<Task>('/tasks', data)
  return response
}

export async function getTasks(params?: TasksQueryParams) {
  const { data } = await api.get('/tasks', { params })
  return {
    items: data.tasks || data.items || [],
    total: data.total || 0,
    page: params?.page || 1,
    limit: params?.limit || 20,
    pages: Math.ceil((data.total || 0) / (params?.limit || 20)),
  }
}

export async function getTask(id: string) {
  const { data } = await api.get<Task>(`/tasks/${id}`)
  return data
}

export async function deleteTask(id: string) {
  const { data } = await api.delete<{ message: string }>(`/tasks/${id}`)
  return data
}

export async function startTask(id: string) {
  const { data } = await api.post<Task>(`/tasks/${id}/start`)
  return data
}

// ─── File Upload ──────────────────────────────────────────────────────
export async function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<{ url: string; filename: string }>(
    '/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event: AxiosProgressEvent) => {
        if (onProgress && event.total) {
          const percent = Math.round((event.loaded * 100) / event.total)
          onProgress(percent)
        }
      },
    }
  )
  return data
}

// ─── Voices ────────────────────────────────────────────────────────────
export interface Voice {
  id: number
  name: string
  description?: string
  voice_type: string
  file_path?: string
  is_default: boolean
  created_at?: string
}

export async function getVoices() {
  const { data } = await api.get<Voice[]>('/voices')
  return data
}

export async function cloneVoice(file: File, name?: string) {
  const formData = new FormData()
  formData.append('file', file)
  if (name) formData.append('name', name)

  const { data } = await api.post<Voice>('/voices', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function recordVoice(blob: Blob, name?: string) {
  const formData = new FormData()
  formData.append('file', blob, 'recorded_voice.webm')
  if (name) formData.append('name', name)

  const { data } = await api.post<Voice>('/voices/record', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deleteVoice(id: number) {
  const { data } = await api.delete<{ message: string; voice_id: number }>(`/voices/${id}`)
  return data
}

// ─── Video Analysis ────────────────────────────────────────────────────
export interface AnalysisResult {
  style?: Record<string, unknown>
  pacing?: Record<string, unknown>
  scenes?: Array<Record<string, unknown>>
  colors?: Record<string, unknown>
  [key: string]: unknown
}

export interface AnalysisResponse {
  task_id: string
  status: string
  result: AnalysisResult
  message?: string
}

export async function analyzeVideo(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<AnalysisResponse>('/analysis/reference', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000, // 5 min for video analysis
  })
  return data
}

export async function getAnalysis(id: string) {
  const { data } = await api.get<AnalysisResponse>(`/analysis/${id}`)
  return data
}

// ─── Highlights ────────────────────────────────────────────────────────
export interface HighlightResult {
  highlights?: string[]
  subtitle_srt?: string
  subtitle_ass?: string
  [key: string]: unknown
}

export async function getHighlights(taskId: string) {
  const { data } = await api.get<HighlightResult>(`/tasks/${taskId}/highlights`)
  return data
}

// ─── Models / ComfyUI ──────────────────────────────────────────────────
export interface ComfyUIModel {
  name: string
  title: string
  type?: string
}

export async function getModels() {
  const { data } = await api.get<ComfyUIModel[]>('/models')
  return data
}

export async function getComfyuiStatus() {
  const { data } = await api.get<{ status: string; queue_remaining?: number }>('/comfyui/status')
  return data
}

// ─── Prompts ───────────────────────────────────────────────────────────
export interface Prompt {
  id: string
  title: string
  content: string
  category?: string
  created_at?: string
}

export async function getPrompts() {
  const { data } = await api.get<Prompt[]>('/prompts')
  return data
}

export async function createPrompt(data: { title: string; content: string; category?: string }) {
  const { data: response } = await api.post<Prompt>('/prompts', data)
  return response
}

// ─── API Keys ──────────────────────────────────────────────────────────
export async function createApiKey(name: string) {
  const { data } = await api.post('/api-keys', { name })
  return data
}

export async function listApiKeys() {
  const { data } = await api.get('/api-keys')
  return data
}

export async function deleteApiKey(id: number) {
  const { data } = await api.delete(`/api-keys/${id}`)
  return data
}

// ─── Webhooks ──────────────────────────────────────────────────────────
export async function registerWebhook(data: { url: string; events: string[] }) {
  const { data: response } = await api.post('/webhooks', data)
  return response
}

export async function listWebhooks() {
  const { data } = await api.get('/webhooks')
  return data
}

export async function updateWebhook(id: number, data: any) {
  const { data: response } = await api.put(`/webhooks/${id}`, data)
  return response
}

export async function deleteWebhook(id: number) {
  const { data } = await api.delete(`/webhooks/${id}`)
  return data
}

export async function testWebhook(id: number) {
  const { data } = await api.post(`/webhooks/${id}/test`)
  return data
}

// ─── Billing ──────────────────────────────────────────────────────────
export async function getPlans() {
  const { data } = await api.get('/billing/plans')
  return data
}

export async function subscribe(plan: string) {
  const { data } = await api.post('/billing/subscribe', { plan })
  return data
}

export async function purchaseCredits(amount: number) {
  const { data } = await api.post('/billing/credits', { amount })
  return data
}

export async function getTransactions() {
  const { data } = await api.get('/billing/transactions')
  return data
}

// ─── Admin ─────────────────────────────────────────────────────────────
export async function getAdminStats() {
  const { data } = await api.get('/admin/stats')
  return data
}

export async function getAdminUsers() {
  const { data } = await api.get('/admin/users')
  return data
}

export async function adjustUserCredits(userId: number, amount: number) {
  const { data } = await api.post(`/admin/users/${userId}/credits`, { amount })
  return data
}

export async function getGPUStatus() {
  const { data } = await api.get('/admin/gpu')
  return data
}

export async function getQueueStatus() {
  const { data } = await api.get('/admin/queue')
  return data
}

export default api
// Backward compatibility aliases
export type TaskResponse = Task
export type VoiceResponse = Voice
export const listTasks = getTasks
export const listVoices = getVoices
