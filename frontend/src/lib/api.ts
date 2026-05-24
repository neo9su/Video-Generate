import axios, { AxiosInstance, AxiosProgressEvent } from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

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
export async function login(email: string, password: string) {
  const { data } = await api.post('/auth/login', { email, password })
  if (data.access_token) {
    setAuthToken(data.access_token)
  }
  return data
}

export async function register(email: string, password: string, name?: string) {
  const { data } = await api.post('/auth/register', { email, password, name })
  return data
}

export async function getProfile() {
  const { data } = await api.get('/auth/profile')
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
  const { data } = await api.get<PaginatedResponse<Task>>('/tasks', { params })
  return data
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
  id: string
  name: string
  language?: string
  gender?: string
  preview_url?: string
  created_at?: string
}

export async function getVoices() {
  const { data } = await api.get<Voice[]>('/voices')
  return data
}

export async function cloneVoice(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<Voice>('/voices/clone', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
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

export default api
