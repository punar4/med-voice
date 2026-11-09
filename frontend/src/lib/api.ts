// Typed client for the backend API. Paths are relative, so the same code works
// in dev (Vite proxies /api to the backend) and in production (FastAPI serves
// the built frontend from the same origin).

export type TimeOfDay = 'morning' | 'afternoon' | 'night'
export type Food = 'before' | 'after' | 'any'

export interface Profile {
  id: number
  elder_name: string
  language: string
  share_token: string
  created_at: string
}

export interface Medicine {
  id: number
  profile_id: number
  name: string
  aliases: string[]
  label: string
  color_word: string
  photo_path: string | null
  dose: string
  times: TimeOfDay[]
  food: Food
  days_total: number | null
  start_date: string | null
  purpose: string | null
  confirmed: boolean
}

// `confirmed` is never sent: only the confirm route may set it.
export type MedicineInput = Omit<Medicine, 'id' | 'profile_id' | 'confirmed'>

export interface ProfileResponse {
  profile: Profile
  medicines: Medicine[]
}

const API_BASE = '/api'

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return 'Some details are missing or not allowed — please check the form.'
  } catch {
    // Fall through to the status text below.
  }
  return `Request failed (${response.status} ${response.statusText}).`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function createProfile(elderName: string): Promise<{ id: number; share_token: string }> {
  return request('/profiles', { method: 'POST', body: JSON.stringify({ elder_name: elderName }) })
}

export function getProfile(profileId: number): Promise<ProfileResponse> {
  return request(`/profiles/${profileId}`)
}

export function addMedicine(profileId: number, input: MedicineInput): Promise<Medicine> {
  return request(`/profiles/${profileId}/medicines`, { method: 'POST', body: JSON.stringify(input) })
}

export function updateMedicine(medicineId: number, input: MedicineInput): Promise<Medicine> {
  return request(`/medicines/${medicineId}`, { method: 'PUT', body: JSON.stringify(input) })
}

export function confirmMedicine(medicineId: number): Promise<Medicine> {
  return request(`/medicines/${medicineId}/confirm`, { method: 'POST' })
}

export function deleteMedicine(medicineId: number): Promise<void> {
  return request(`/medicines/${medicineId}`, { method: 'DELETE' })
}
