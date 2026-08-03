import { api } from '@/lib/api/client'
import type { Branch } from '@/lib/api/types'

export interface BranchInput {
  name: string
  code: string
  address?: string
  phone?: string
}

export const branchesApi = {
  list: () => api.list<Branch>('/branches'),
  create: (payload: BranchInput) => api.post<Branch>('/branches', payload),
  update: (id: string, payload: Partial<BranchInput>) =>
    api.patch<Branch>(`/branches/${id}`, payload),
  remove: (id: string) => api.delete(`/branches/${id}`),
}
