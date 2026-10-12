import { useEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { queryKeys } from '@/lib/api/queryKeys'
import { fetchBlob } from './api'

/**
 * Bola rasmlari ochiq URL'da turmaydi: har biri tokenli so'rov bilan blob
 * sifatida olinadi va faqat shu brauzer xotirasida `blob:` URL bo'ladi.
 */
export function useAuthedImage(path: string | null | undefined): {
  url: string | null
  isLoading: boolean
  isError: boolean
} {
  const organizationId = useOrganizationId()
  const query = useQuery({
    queryKey: queryKeys.blob(organizationId, path ?? ''),
    queryFn: () => fetchBlob(path as string),
    enabled: Boolean(path),
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
    retry: false,
  })

  const url = useMemo(
    () => (query.data ? URL.createObjectURL(query.data) : null),
    [query.data],
  )
  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])

  return { url, isLoading: query.isLoading, isError: query.isError }
}

/** Bo'limdagi barcha so'rovlarni yangilash (bitta `invalidate`). */
export function useInvalidateMemories() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  return () =>
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'memories'] })
}
