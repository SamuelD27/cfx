import axios, { AxiosInstance } from 'axios'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Check if auth is enabled before redirecting
      try {
        const configResponse = await fetch('/api/auth/config')
        if (configResponse.ok) {
          const config = await configResponse.json()
          if (config.auth_enabled) {
            // Only redirect to login if auth is actually enabled
            localStorage.removeItem('auth_token')
            window.location.href = '/login'
          }
          // If auth is disabled, don't redirect - just let the error propagate
        }
      } catch {
        // If we can't check auth config, don't redirect
        console.warn('Could not check auth config, not redirecting on 401')
      }
    }
    return Promise.reject(error)
  }
)

// Types
export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
}

export interface Character {
  id: number
  name: string
  status: string
  work_dir: string
  created_at: string
  completed_at?: string
}

export interface TrainingSession {
  id: number
  character_id: number
  status: string
  progress: number
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface InferenceJob {
  id: number
  character_id: number
  character_name: string
  prompt: string
  optimized_prompt?: string
  status: string
  output_paths?: string[]
  lora_weight: number
  test_dim: number
  batch_size: number
  created_at: string
  completed_at?: string
}

export interface MediaFile {
  filename: string
  original_filename: string
  file_path: string
  file_url: string
  file_size: number
  content_type: string
  width?: number
  height?: number
}

// Auth API
export const authApi = {
  login: (credentials: { username: string; password: string }): Promise<LoginResponse> =>
    api.post('/auth/login', new URLSearchParams(credentials)).then(res => res.data),
  
  register: (data: { username: string; email: string; password: string }): Promise<User> =>
    api.post('/auth/register', data).then(res => res.data),
  
  getMe: (): Promise<User> =>
    api.get('/auth/me').then(res => res.data),
  
  verifyToken: (): Promise<{ valid: boolean; user: string }> =>
    api.get('/auth/verify').then(res => res.data),
}

// Characters API
export const charactersApi = {
  list: (): Promise<Character[]> =>
    api.get('/training/characters').then(res => res.data),
  
  create: (data: { name: string; input_image_path: string }): Promise<Character> =>
    api.post('/training/characters', data).then(res => res.data),
  
  get: (id: number): Promise<Character> =>
    api.get(`/training/characters/${id}`).then(res => res.data),
  
  getInfo: (id: number): Promise<any> =>
    api.get(`/inference/characters/${id}/info`).then(res => res.data),
  
  getAvailable: (): Promise<any[]> =>
    api.get('/inference/available-characters').then(res => res.data),
}

// Training API
export const trainingApi = {
  startTraining: (characterId: number, config: any): Promise<TrainingSession> =>
    api.post(`/training/characters/${characterId}/train`, { character_id: characterId, ...config }).then(res => res.data),

  getTrainingSessions: (characterId: number): Promise<TrainingSession[]> =>
    api.get(`/training/characters/${characterId}/training`).then(res => res.data),

  getTrainingSession: (sessionId: number): Promise<TrainingSession> =>
    api.get(`/training/training/${sessionId}`).then(res => res.data),
}

// Models API
export const modelsApi = {
  getModels: (): Promise<any> =>
    api.get('/models').then(res => res.data),

  getSchedulers: (): Promise<any> =>
    api.get('/models/schedulers').then(res => res.data),

  getOptimizers: (): Promise<any> =>
    api.get('/models/optimizers').then(res => res.data),

  getTrainers: (): Promise<any> =>
    api.get('/models/trainers').then(res => res.data),

  validateModel: (modelPath: string): Promise<any> =>
    api.post('/models/validate-model', { model_path: modelPath }).then(res => res.data),
}

// Inference API
export const inferenceApi = {
  generate: (config: any): Promise<InferenceJob> =>
    api.post('/inference/generate', config).then(res => res.data),
  
  listJobs: (characterId?: number, limit = 50, offset = 0): Promise<InferenceJob[]> =>
    api.get('/inference/jobs', { params: { character_id: characterId, limit, offset } }).then(res => res.data),
  
  getJob: (jobId: number): Promise<InferenceJob> =>
    api.get(`/inference/jobs/${jobId}`).then(res => res.data),
}

// Media API
export const mediaApi = {
  upload: (file: File): Promise<MediaFile> => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data)
  },
  
  list: (): Promise<{ files: MediaFile[]; total: number }> =>
    api.get('/media/files').then(res => res.data),
  
  delete: (filename: string): Promise<{ message: string }> =>
    api.delete(`/media/files/${filename}`).then(res => res.data),
  
  processImage: (data: any): Promise<MediaFile> =>
    api.post('/media/process-image', data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data),
}

// Settings API
export const settingsApi = {
  saveSetting: (data: { key: string; value: string; is_sensitive?: boolean }): Promise<{ message: string }> =>
    api.post('/settings/setting', data).then(res => res.data),
  
  getSetting: (key: string): Promise<{ key: string; value: string; is_sensitive: boolean }> =>
    api.get(`/settings/setting/${key}`).then(res => res.data),
  
  getAllSettings: (): Promise<Record<string, { value: string; is_sensitive: boolean }>> =>
    api.get('/settings/settings').then(res => res.data),
  
  deleteSetting: (key: string): Promise<{ message: string }> =>
    api.delete(`/settings/setting/${key}`).then(res => res.data),
  
  saveEnvironment: (data: any): Promise<any> =>
    api.post('/settings/environment', data).then(res => res.data),
  
  getEnvironment: (): Promise<any> =>
    api.get('/settings/environment').then(res => res.data),
  
  testEnvironment: (): Promise<Record<string, { valid: boolean; message: string }>> =>
    api.get('/settings/test-environment').then(res => res.data),
}

// Dataset API
export interface Dataset {
  id: number
  name: string
  trigger_word: string
  caption_template: string
  auto_caption: boolean
  resize_images: boolean
  crop_images: boolean
  flip_images: boolean
  quality_filter: string
  image_count: number
  status: string
  created_at: string
  updated_at: string
}

export interface DatasetImage {
  id: number
  filename: string
  original_filename: string
  caption: string | null
  processed: boolean
  created_at: string
}

export interface CreateDatasetRequest {
  name: string
  trigger_word: string
  caption_template: string
  auto_caption: boolean
  resize_images: boolean
  crop_images: boolean
  flip_images: boolean
  quality_filter: string
  selected_images: string[]
}

export const datasetApi = {
  createDataset: (data: CreateDatasetRequest): Promise<Dataset> =>
    api.post('/datasets/datasets', data).then(res => res.data),

  getDatasets: (): Promise<{ datasets: Dataset[]; total: number }> =>
    api.get('/datasets/datasets').then(res => res.data),

  getDataset: (id: number): Promise<Dataset> =>
    api.get(`/datasets/datasets/${id}`).then(res => res.data),

  getDatasetImages: (id: number): Promise<DatasetImage[]> =>
    api.get(`/datasets/datasets/${id}/images`).then(res => res.data),

  updateTriggerWord: (id: number, trigger_word: string): Promise<{ message: string }> =>
    api.put(`/datasets/datasets/${id}/trigger-word`, { trigger_word }).then(res => res.data),

  updateImageCaption: (datasetId: number, imageId: number, caption: string): Promise<{ message: string }> =>
    api.put(`/datasets/datasets/${datasetId}/images/${imageId}/caption`, { caption }).then(res => res.data),

  deleteDataset: (id: number): Promise<{ message: string }> =>
    api.delete(`/datasets/datasets/${id}`).then(res => res.data),
}

export { api }
export default api
