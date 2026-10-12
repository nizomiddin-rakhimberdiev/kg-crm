/**
 * Kuzatuv: ulangan kameralarning holati va so'nggi kadri (taxminan jonli).
 *
 * Bu haqiqiy video emas: kamera har bir necha soniyada bitta kadr yuboradi,
 * serverda faqat so'nggisi turadi. Ko'rish `memories.read` huquqi bilan
 * cheklangan (backend ham tekshiradi), kadr brauzer keshida qolmaydi va
 * kuzatuv har kamera uchun alohida, ongli ravishda yoqiladi.
 */

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Cctv, EyeOff, Maximize2, Siren } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Badge, Button, Card } from '@/components/ui/primitives'
import { EmptyState } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { queryKeys } from '@/lib/api/queryKeys'
import type { Camera } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { formatDateTime } from '@/lib/utils'
import { camerasApi, eventsApi } from '../api'
import { useInvalidateMemories } from '../hooks'
import { fadeUp, stagger } from '../motion'
import { AuthedImage, ErrorBanner, SectionTitle, Skeleton, errorText } from './shared'

function frameClass(extra = '') {
  return `aspect-video w-full rounded-xl bg-slate-900 object-cover ${extra}`
}

function Frame({ camera, big = false }: { camera: Camera; big?: boolean }) {
  if (camera.has_preview && camera.preview_at) {
    return (
      <AuthedImage
        // `v` kadr yangilanganda kalitni almashtiradi; server uni e'tiborsiz qoldiradi.
        path={`${camerasApi.previewPath(camera.id)}?v=${encodeURIComponent(camera.preview_at)}`}
        alt={camera.name}
        className={frameClass(big ? 'max-h-[70vh]' : '')}
      />
    )
  }
  return (
    <div className={frameClass('grid place-items-center text-slate-400')}>
      <div className="px-4 text-center">
        <EyeOff className="mx-auto h-6 w-6" />
        <p className="mt-2 text-xs">
          {camera.preview_enabled ? t('Kadr kutilmoqda…') : t('Kuzatuv o‘chiq')}
        </p>
      </div>
    </div>
  )
}

export function SurveillancePanel() {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const invalidate = useInvalidateMemories()
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState<string | null>(null)

  const cameras = useQuery({
    queryKey: queryKeys.cameras(organizationId),
    queryFn: camerasApi.list,
    refetchInterval: 10_000, // `preview_at` o'zgarsa tasvir yangilanadi
  })
  const events = useQuery({
    queryKey: queryKeys.cameraEvents(organizationId, { status: 'new', page_size: 100 }),
    queryFn: () => eventsApi.list({ status: 'new', page_size: 100 }),
    refetchInterval: 15_000,
  })
  const enable = useMutation({
    mutationFn: (id: string) => camerasApi.setPreview(id, true),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorText(err)),
  })

  const rows = (cameras.data?.items ?? []).filter((c) => c.is_active)
  const online = rows.filter((c) => c.is_online).length
  const newByCamera = new Map<string, number>()
  for (const event of events.data?.items ?? []) {
    if (event.camera) newByCamera.set(event.camera, (newByCamera.get(event.camera) ?? 0) + 1)
  }
  const open = rows.find((c) => c.id === openId) ?? null

  return (
    <section className="space-y-4">
      <SectionTitle
        title={t('Kuzatuv')}
        hint={t('Ulangan kameralar holati va so‘nggi kadri. Haqiqiy video emas: kadr bir necha soniyada yangilanadi.')}
      >
        {rows.length > 0 && (
          <Badge tone={online > 0 ? 'success' : 'neutral'}>
            {`${online} / ${rows.length} ${t('onlayn')}`}
          </Badge>
        )}
      </SectionTitle>

      <ErrorBanner message={error} />

      {cameras.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <Card>
          <EmptyState
            icon={Cctv}
            title={t('Kamera ulanmagan')}
            hint={t('Xavfsizlik bo‘limida kamera qo‘shing va uni ulang — shu yerda ko‘rinadi.')}
          />
        </Card>
      ) : (
        <motion.ul
          variants={stagger()}
          initial="hidden"
          animate="show"
          className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
        >
          {rows.map((camera) => {
            const fresh = newByCamera.get(camera.id) ?? 0
            return (
              <motion.li key={camera.id} variants={fadeUp}>
                <Card className="space-y-3 p-3">
                  <div className="relative">
                    <Frame camera={camera} />
                    {camera.has_preview && (
                      <button
                        type="button"
                        onClick={() => setOpenId(camera.id)}
                        aria-label={t('Kattalashtirish')}
                        className="absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-lg bg-black/50 text-white transition-colors hover:bg-black/70"
                      >
                        <Maximize2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                  <div className="flex items-start justify-between gap-2 px-1">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">{camera.name}</p>
                      <p className="truncate text-xs text-slate-500">
                        {camera.location || t('Joylashuv ko‘rsatilmagan')}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                      {fresh > 0 && (
                        <Badge tone="danger">
                          <Siren className="mr-1 inline h-3 w-3" />
                          {fresh}
                        </Badge>
                      )}
                      <Badge tone={camera.is_online ? 'success' : 'neutral'}>
                        {camera.is_online ? t('Onlayn') : t('Oflayn')}
                      </Badge>
                    </div>
                  </div>
                  {camera.has_token && !camera.preview_enabled && can('memories.update') && (
                    <Button
                      variant="outline"
                      disabled={enable.isPending}
                      onClick={() => enable.mutate(camera.id)}
                      className="w-full"
                    >
                      {t('Kuzatuvni yoqish')}
                    </Button>
                  )}
                </Card>
              </motion.li>
            )
          })}
        </motion.ul>
      )}

      <Modal open={open !== null} onClose={() => setOpenId(null)} className="max-w-4xl">
        {open && (
          <div className="space-y-3 p-5">
            <div className="pr-8">
              <h3 className="text-lg font-semibold text-slate-900">{open.name}</h3>
              <p className="text-xs text-slate-500">
                {open.preview_at ? formatDateTime(open.preview_at) : ''}
              </p>
            </div>
            <Frame camera={open} big />
          </div>
        )}
      </Modal>
    </section>
  )
}

export default SurveillancePanel
