/**
 * Rasmlar: yuklash, avtomatik tanish natijasi va o'qituvchi tekshiruvi.
 *
 * Ishonchi past taklif ("suggested") ota-onaga AVTOMATIK ketmaydi — u shu
 * yerda odam tasdiqlagandan keyingina yuboriladi. Bola faqat vasiy
 * roziligi bo'lsa tanlanadi (backend ham tekshiradi).
 */

import { useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ImagePlus,
  Loader2,
  RefreshCw,
  Send,
  Trash2,
  UserCheck,
  X,
} from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { Badge, Button, Card, Select } from '@/components/ui/primitives'
import { EmptyState } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { queryKeys } from '@/lib/api/queryKeys'
import type { MemoryPhoto, PhotoTag } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDateTime } from '@/lib/utils'
import { consentsApi, memoryPhotosApi, photoTagsApi } from '../api'
import { useInvalidateMemories } from '../hooks'
import { popIn, stagger } from '../motion'
import { AuthedImage, ErrorBanner, SectionTitle, Skeleton, errorText } from './shared'

type Filter = 'all' | 'review' | 'untagged'

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: t('Hammasi') },
  { id: 'review', label: t('Tekshirish kerak') },
  { id: 'untagged', label: t('Bolasiz') },
]

const needsReview = (photo: MemoryPhoto) => photo.tags.some((tag) => tag.status === 'suggested')
const confirmedTags = (photo: MemoryPhoto) => photo.tags.filter((tag) => tag.status === 'confirmed')

export function PhotosPanel() {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const { toast } = useToast()
  const invalidate = useInvalidateMemories()
  const inputRef = useRef<HTMLInputElement>(null)

  const [filter, setFilter] = useState<Filter>('all')
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(0)
  const [dragging, setDragging] = useState(false)

  const params = { page, page_size: 24 }
  const query = useQuery({
    queryKey: queryKeys.memoryPhotos(organizationId, params),
    queryFn: () => memoryPhotosApi.list(params),
    // Tanish fonda ketadi: "kutilmoqda" bor ekan, ro'yxat o'zi yangilanib turadi.
    refetchInterval: (q) =>
      q.state.data?.items.some((p) => p.status === 'pending') ? 3000 : false,
  })

  const all = query.data?.items ?? []
  const photos = all.filter((p) =>
    filter === 'review' ? needsReview(p) : filter === 'untagged' ? confirmedTags(p).length === 0 : true,
  )
  const selected = all.find((p) => p.id === selectedId) ?? null
  const pagination = query.data?.pagination

  async function uploadFiles(files: FileList | File[]) {
    setError(null)
    const list = Array.from(files).filter((f) => f.type.startsWith('image/'))
    if (list.length === 0) {
      setError(t('Faqat rasm fayllarini tanlang.'))
      return
    }
    setUploading((n) => n + list.length)
    let ok = 0
    for (const file of list) {
      try {
        await memoryPhotosApi.upload(file)
        ok += 1
      } catch (err) {
        setError(errorText(err))
      } finally {
        setUploading((n) => n - 1)
      }
    }
    if (ok > 0) toast(t('{count} ta rasm yuklandi.', { count: ok }))
    setPage(1)
    invalidate()
  }

  return (
    <div className="space-y-4">
      <SectionTitle
        title={t('Rasmlar')}
        hint={t("O'qituvchi guruhga yuborgan va qo'lda yuklangan rasmlar — tanish natijasi bilan.")}
      >
        {can('memories.create') && (
          <>
            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              hidden
              onChange={(e) => {
                if (e.target.files) void uploadFiles(e.target.files)
                e.target.value = ''
              }}
            />
            <Button icon={uploading ? Loader2 : ImagePlus} onClick={() => inputRef.current?.click()}>
              {uploading ? t('Yuklanmoqda…') : t('Rasm yuklash')}
            </Button>
          </>
        )}
      </SectionTitle>

      <ErrorBanner message={error} />

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={cn(
              'rounded-full border px-3 py-1 text-sm font-medium transition-colors',
              filter === f.id
                ? 'border-brand-600 bg-brand-50 text-brand-700'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50',
            )}
          >
            {f.label}
            {f.id === 'review' && all.filter(needsReview).length > 0 && (
              <span className="ml-1.5 rounded-full bg-orik-100 px-1.5 text-[11px] text-orik-700">
                {all.filter(needsReview).length}
              </span>
            )}
          </button>
        ))}
      </div>

      <div
        onDragOver={(e) => {
          if (!can('memories.create')) return
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          if (can('memories.create')) void uploadFiles(e.dataTransfer.files)
        }}
        className={cn(
          'rounded-2xl border-2 border-dashed p-1 transition-colors',
          dragging ? 'border-brand-400 bg-brand-50/60' : 'border-transparent',
        )}
      >
        {query.isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="aspect-square" />
            ))}
          </div>
        ) : query.isError ? (
          <ErrorBanner message={errorText(query.error)} />
        ) : photos.length === 0 ? (
          <Card>
            <EmptyState
              icon={ImagePlus}
              title={t("Hozircha rasm yo'q")}
              hint={t(
                "Telegram guruhiga rasm yuboring yoki bu yerga sudrab tashlang — Radix bolalarni taniydi.",
              )}
            />
          </Card>
        ) : (
          <motion.ul
            variants={stagger(0.03)}
            initial="hidden"
            animate="show"
            className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
          >
            {photos.map((photo) => (
              <PhotoTile key={photo.id} photo={photo} onOpen={() => setSelectedId(photo.id)} />
            ))}
          </motion.ul>
        )}
      </div>

      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-center gap-3 text-sm text-slate-600">
          <Button variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t('Oldingi')}
          </Button>
          <span>
            {page} / {pagination.total_pages}
          </span>
          <Button
            variant="outline"
            disabled={page >= pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            {t('Keyingi')}
          </Button>
        </div>
      )}

      <PhotoModal photo={selected} onClose={() => setSelectedId(null)} />
    </div>
  )
}

function PhotoTile({ photo, onOpen }: { photo: MemoryPhoto; onOpen: () => void }) {
  const confirmed = confirmedTags(photo)
  return (
    <motion.li variants={popIn} layout>
      <button
        type="button"
        onClick={onOpen}
        className="group relative block aspect-square w-full overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 text-left shadow-card transition-shadow hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40"
      >
        <AuthedImage
          path={memoryPhotosApi.imagePath(photo.id)}
          alt={photo.caption || formatDateTime(photo.taken_at)}
          className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.06]"
        />
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-900/75 to-transparent p-2.5 pt-8 text-white">
          <p className="truncate text-xs font-medium">
            {confirmed.length > 0
              ? confirmed.map((tag) => tag.child_name).join(', ')
              : t('Bola belgilanmagan')}
          </p>
          <p className="text-[11px] text-white/70">{formatDateTime(photo.taken_at)}</p>
        </div>
        <div className="absolute left-2 top-2 flex gap-1.5">
          {photo.status === 'pending' && (
            <Badge tone="info">
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              {t('Tahlil')}
            </Badge>
          )}
          {needsReview(photo) && <Badge tone="warning">{t('Tekshiring')}</Badge>}
          {photo.status === 'failed' && <Badge tone="danger">{t('Xato')}</Badge>}
        </div>
      </button>
    </motion.li>
  )
}

function PhotoModal({ photo, onClose }: { photo: MemoryPhoto | null; onClose: () => void }) {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const { toast } = useToast()
  const invalidate = useInvalidateMemories()
  const [error, setError] = useState<string | null>(null)
  const [manualChild, setManualChild] = useState('')

  const consents = useQuery({
    queryKey: queryKeys.faceConsents(organizationId),
    queryFn: consentsApi.list,
    enabled: Boolean(photo) && can('memories.update'),
  })
  const consented = (consents.data?.items ?? []).filter((c) => !c.revoked_at)

  const onError = (err: unknown) => setError(errorText(err))
  const done = (message?: string) => {
    setError(null)
    if (message) toast(message)
    invalidate()
  }

  const confirm = useMutation({
    mutationFn: photoTagsApi.confirm,
    onSuccess: () => done(t('Tasdiqlandi — ota-onaga yuboriladi.')),
    onError,
  })
  const reject = useMutation({
    mutationFn: photoTagsApi.reject,
    onSuccess: () => done(),
    onError,
  })
  const tag = useMutation({
    mutationFn: ({ id, childId }: { id: string; childId: string }) =>
      memoryPhotosApi.tag(id, childId),
    onSuccess: () => {
      setManualChild('')
      done(t('Bola belgilandi — ota-onaga yuboriladi.'))
    },
    onError,
  })
  const reprocess = useMutation({
    mutationFn: memoryPhotosApi.reprocess,
    onSuccess: (r) => done(t('Qayta tahlil: {matched} ta bola aniqlandi.', { matched: r.matched })),
    onError,
  })
  const remove = useMutation({
    mutationFn: memoryPhotosApi.remove,
    onSuccess: () => {
      done(t("Rasm o'chirildi."))
      onClose()
    },
    onError,
  })

  const visibleTags = (photo?.tags ?? []).filter((x) => x.status !== 'rejected')

  return (
    <Modal open={Boolean(photo)} onClose={onClose} className="max-w-3xl">
      {photo && (
        <div className="grid gap-0 md:grid-cols-[1.4fr_1fr]">
          <AuthedImage
            path={memoryPhotosApi.imagePath(photo.id)}
            alt={photo.caption || formatDateTime(photo.taken_at)}
            className="max-h-[70vh] w-full bg-slate-900 object-contain md:rounded-l-2xl"
          />
          <div className="space-y-4 p-5">
            <div>
              <h3 className="text-base font-semibold text-slate-900">{t('Rasm tafsiloti')}</h3>
              <p className="mt-0.5 text-sm text-slate-500">{formatDateTime(photo.taken_at)}</p>
              <p className="mt-1 text-xs text-slate-400">
                {photo.source === 'telegram' ? t('Telegram guruhi') : t('Yuklangan')} ·{' '}
                {t('{count} ta yuz topildi', { count: photo.faces_detected })}
              </p>
            </div>

            <ErrorBanner message={error} />

            <ul className="space-y-2">
              <AnimatePresence initial={false}>
                {visibleTags.map((item) => (
                  <TagRow
                    key={item.id}
                    tag={item}
                    canEdit={can('memories.update')}
                    busy={confirm.isPending || reject.isPending}
                    onConfirm={() => confirm.mutate(item.id)}
                    onReject={() => reject.mutate(item.id)}
                  />
                ))}
              </AnimatePresence>
              {visibleTags.length === 0 && (
                <li className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-500">
                  {t('Taniladigan bola topilmadi.')}
                </li>
              )}
            </ul>

            {can('memories.update') && (
              <div className="space-y-2 border-t border-slate-100 pt-4">
                <p className="text-sm font-medium text-slate-700">{t("Bolani qo'lda belgilash")}</p>
                <Select
                  placeholder={t('Bolani tanlang')}
                  value={manualChild}
                  onChange={setManualChild}
                  options={consented.map((c) => ({ value: c.child, label: c.child_name }))}
                />
                {consented.length === 0 && (
                  <p className="text-xs text-slate-400">
                    {t("Avval «Yuz roziligi» bo'limida vasiy roziligini kiriting.")}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button
                    icon={UserCheck}
                    disabled={!manualChild || tag.isPending}
                    onClick={() => tag.mutate({ id: photo.id, childId: manualChild })}
                  >
                    {t('Belgilash')}
                  </Button>
                  <Button
                    variant="outline"
                    icon={RefreshCw}
                    disabled={reprocess.isPending}
                    onClick={() => reprocess.mutate(photo.id)}
                  >
                    {t('Qayta tahlil')}
                  </Button>
                </div>
              </div>
            )}

            {can('memories.delete') && (
              <Button
                variant="ghost"
                icon={Trash2}
                className="text-red-600 hover:bg-red-50"
                disabled={remove.isPending}
                onClick={() => remove.mutate(photo.id)}
              >
                {t("Rasmni o'chirish")}
              </Button>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}

function TagRow({
  tag,
  canEdit,
  busy,
  onConfirm,
  onReject,
}: {
  tag: PhotoTag
  canEdit: boolean
  busy: boolean
  onConfirm: () => void
  onReject: () => void
}) {
  const percent = Math.round(tag.confidence * 100)
  return (
    <motion.li
      layout
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -12 }}
      className="rounded-xl border border-slate-200 p-3"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-medium text-slate-800">{tag.child_name}</span>
        {tag.status === 'confirmed' ? (
          <Badge tone="success">
            {tag.sent_at ? t('Yuborilgan') : t('Tasdiqlangan')}
          </Badge>
        ) : (
          <Badge tone="warning">{t('Taklif')}</Badge>
        )}
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden>
        <motion.div
          className={cn('h-full rounded-full', percent >= 70 ? 'bg-nihol-500' : 'bg-orik-500')}
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      <p className="mt-1 text-[11px] text-slate-400">
        {t('Ishonch: {percent}%', { percent })}
      </p>
      {tag.status === 'suggested' && canEdit && (
        <div className="mt-2 flex gap-2">
          <Button icon={Send} disabled={busy} onClick={onConfirm} className="px-3 py-1.5">
            {t('Tasdiqlash va yuborish')}
          </Button>
          <Button
            variant="outline"
            icon={X}
            disabled={busy}
            onClick={onReject}
            className="px-3 py-1.5"
            aria-label={t('Rad etish')}
          />
        </div>
      )}
    </motion.li>
  )
}

export default PhotosPanel
