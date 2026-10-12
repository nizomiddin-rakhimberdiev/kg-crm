/** Radix AI endpointlari (docs/08 §6). Rasm yuklash — multipart, shuning uchun `httpClient`. */

import { api, httpClient } from '@/lib/api/client'
import type {
  Camera,
  CameraEvent,
  ChatKind,
  Envelope,
  FaceConsent,
  MemoryPhoto,
  PairingLink,
  PhotoTag,
  ScheduleItem,
  ScheduleKind,
  TelegramChat,
} from '@/lib/api/types'

async function upload<T>(url: string, fields: Record<string, string | Blob | undefined>) {
  const form = new FormData()
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined && value !== '') form.append(key, value)
  }
  const response = await httpClient.post<Envelope<T>>(url, form, {
    headers: { 'Content-Type': undefined },
    timeout: 120_000,
  })
  return response.data.data
}

/** Autentifikatsiyali rasm: ochiq URL yo'q, shuning uchun blob sifatida olinadi. */
export async function fetchBlob(path: string): Promise<Blob> {
  const response = await httpClient.get<Blob>(path, { responseType: 'blob' })
  return response.data
}

export const memoryPhotosApi = {
  list: (params?: Record<string, unknown>) => api.list<MemoryPhoto>('/memory-photos', params),
  upload: (image: File, caption?: string) =>
    upload<MemoryPhoto>('/memory-photos', { image, caption }),
  remove: (id: string) => api.delete(`/memory-photos/${id}`),
  reprocess: (id: string) =>
    api.post<{ matched: number; unknown: number; sent: number }>(`/memory-photos/${id}/reprocess`),
  tag: (id: string, childId: string) =>
    api.post<PhotoTag>(`/memory-photos/${id}/tag`, { child_id: childId }),
  imagePath: (id: string) => `/memory-photos/${id}/image`,
}

export const photoTagsApi = {
  confirm: (id: string) => api.post<PhotoTag>(`/photo-tags/${id}/confirm`),
  reject: (id: string) => api.post<PhotoTag>(`/photo-tags/${id}/reject`),
}

export const consentsApi = {
  list: () => api.list<FaceConsent>('/face-consents', { page_size: 100 }),
  grant: (childId: string, guardianId: string) =>
    api.post<FaceConsent>('/face-consents', { child_id: childId, guardian_id: guardianId }),
  revoke: (id: string) => api.post<FaceConsent>(`/face-consents/${id}/revoke`),
  enroll: (id: string, image: File) => upload<FaceConsent>(`/face-consents/${id}/enroll`, { image }),
}

export interface ScheduleInput {
  kind: ScheduleKind
  on_date: string
  at_time: string | null
  title: string
  details: string
  notify: boolean
}

export const scheduleApi = {
  list: (date: string) =>
    api.list<ScheduleItem>('/schedule-items', { on_date: date, page_size: 100 }),
  create: (payload: ScheduleInput) => api.post<ScheduleItem>('/schedule-items', payload),
  remove: (id: string) => api.delete(`/schedule-items/${id}`),
}

export const camerasApi = {
  list: () => api.list<Camera>('/cameras', { page_size: 100 }),
  create: (payload: { name: string; location: string; stream_url: string }) =>
    api.post<Camera>('/cameras', payload),
  remove: (id: string) => api.delete(`/cameras/${id}`),
  issueToken: (id: string, connection: 'edge' | 'webhook') =>
    api.post<{ token: string; connection: 'edge' | 'webhook' }>(`/cameras/${id}/token`, {
      connection,
    }),
  setPreview: (id: string, enabled: boolean) =>
    api.patch<Camera>(`/cameras/${id}`, { preview_enabled: enabled }),
  previewPath: (id: string) => `/cameras/${id}/preview`,
  revokeToken: (id: string) => api.post<Camera>(`/cameras/${id}/revoke-token`),
}

export const eventsApi = {
  list: (params?: Record<string, unknown>) => api.list<CameraEvent>('/camera-events', params),
  create: (fields: {
    kind: string
    severity: string
    note: string
    camera_id?: string
    snapshot?: File
  }) => upload<CameraEvent>('/camera-events', fields),
  acknowledge: (id: string) => api.post<CameraEvent>(`/camera-events/${id}/acknowledge`),
  dismiss: (id: string) => api.post<CameraEvent>(`/camera-events/${id}/dismiss`),
  snapshotPath: (id: string) => `/camera-events/${id}/snapshot`,
}

export const telegramApi = {
  list: () => api.list<TelegramChat>('/telegram-chats', { page_size: 100 }),
  remove: (id: string) => api.delete(`/telegram-chats/${id}`),
  pairing: (kind: ChatKind, guardianId?: string) =>
    api.post<PairingLink>('/telegram-chats/pairing', {
      kind,
      ...(guardianId ? { guardian_id: guardianId } : {}),
    }),
}
