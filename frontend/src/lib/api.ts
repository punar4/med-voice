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

// Every outcome /ask can return (see the T4 entry in docs/LEARN.md).
export type AskOutcome =
  | 'answered'
  | 'clarify_which'
  | 'clarify_question'
  | 'clarify_repeat'
  | 'referral'
  | 'emergency'
  | 'error'

export interface QuestionLog {
  id: number
  profile_id: number
  created_at: string
  transcript: string
  intent: string
  medicine_id: number | null
  outcome: AskOutcome
  answer_key: string
  answer_text: string
}

export interface AskResponse {
  transcript: string
  outcome: AskOutcome
  answer_text: string
  audio_base64: string | null
  medicine: { label: string; photo_url: string | null } | null
  // True when Timbre failed: the text is still correct, only the voice is missing.
  audio_error: boolean
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
  // Only JSON bodies get a Content-Type here; FormData must set its own boundary.
  const isJson = typeof init?.body === 'string'
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: isJson ? { 'Content-Type': 'application/json', ...init?.headers } : init?.headers,
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

// Caregiver's log: every question the elder asked, newest first (capped by the API).
export function getQuestionLog(profileId: number): Promise<QuestionLog[]> {
  return request(`/profiles/${profileId}/log`)
}

// The elder's one action: send the recorded question, get the spoken answer.
export function askElder(token: string, recording: Blob): Promise<AskResponse> {
  const form = new FormData()
  form.append('audio', recording, 'audio.wav')
  return request(`/elder/${encodeURIComponent(token)}/ask`, { method: 'POST', body: form })
}
