/** Contract templates and contracts (PLAN 6.5). */

import { api } from '@/lib/api/client'

export interface ContractTemplate {
  id: string
  name: string
  language: 'uz' | 'ru' | 'en'
  body: string
  version: number
  is_active: boolean
  updated_at: string
}

export type ContractStatus = 'draft' | 'signed' | 'terminated'

export interface Contract {
  id: string
  number: string
  child: string
  child_name: string
  guardian: string | null
  guardian_name: string
  template: string
  template_name: string
  template_version: number
  /** Frozen at creation — never changes, even if the tariff does. */
  rendered_text: string
  status: ContractStatus
  signed_on: string | null
  terminated_on: string | null
  termination_reason: string
  created_at: string
}

export const contractTemplatesApi = {
  list: () => api.get<ContractTemplate[]>('/contract-templates'),
  placeholders: () => api.get<string[]>('/contract-templates/placeholders'),
  create: (body: Pick<ContractTemplate, 'name' | 'language' | 'body'>) =>
    api.post<ContractTemplate>('/contract-templates', body),
  update: (id: string, body: Pick<ContractTemplate, 'name' | 'language' | 'body'>) =>
    api.patch<ContractTemplate>(`/contract-templates/${id}`, body),
  remove: (id: string) => api.delete(`/contract-templates/${id}`),
}

export const contractsApi = {
  forChild: (childId: string) => api.get<Contract[]>('/contracts', { child: childId }),
  create: (childId: string, templateId: string) =>
    api.post<Contract>('/contracts', { child_id: childId, template_id: templateId }),
  sign: (id: string, signedOn: string) =>
    api.post<Contract>(`/contracts/${id}/sign`, { signed_on: signedOn }),
  terminate: (id: string, terminatedOn: string, reason: string) =>
    api.post<Contract>(`/contracts/${id}/terminate`, {
      terminated_on: terminatedOn,
      reason,
    }),
}

/**
 * Prints the contract through the browser (decision D1 — no PDF library).
 *
 * The text goes in as a text node, never as HTML: a value typed into a
 * child's card must not become markup on a print-out.
 */
export function printContract(contract: Pick<Contract, 'number' | 'rendered_text'>): void {
  const win = window.open('', '_blank', 'noopener=no,width=800,height=900')
  if (!win) return
  win.document.title = contract.number
  const pre = win.document.createElement('pre')
  pre.textContent = contract.rendered_text
  pre.style.whiteSpace = 'pre-wrap'
  pre.style.fontFamily = 'Georgia, "Times New Roman", serif'
  pre.style.fontSize = '14px'
  pre.style.lineHeight = '1.6'
  pre.style.margin = '24px'
  win.document.body.appendChild(pre)
  win.focus()
  win.print()
}
