/**
 * Xavfsizlik: kamera hodisalari (xodim qoidabuzarligi, bolaning yig'lashi)
 * va kameralar ro'yxati.
 *
 * Hodisani kamera tahlilchisi (edge-worker) `POST /camera-events` bilan
 * yuboradi; backend rahbarning Telegram'iga rasm dalili bilan xabar beradi.
 * Bu yerda odam ko'rib chiqadi: "ko'rildi" yoki "noto'g'ri signal".
 */

import { useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import {
  CheckCheck,
  Cctv,
  Frown,
  Link2,
  Plus,
  ShieldAlert,
  Trash2,
  UserX,
  XCircle,
} from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { Badge, Button, Card, Select, type BadgeTone } from '@/components/ui/primitives'
import { EmptyState } from '@/components/ui/EmptyState'
import { Field, TextInput } from '@/components/ui/form'
import { Modal } from '@/components/ui/Modal'
import { queryKeys } from '@/lib/api/queryKeys'
import type { Camera, CameraEvent, EventKind, EventSeverity, EventStatus } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDateTime } from '@/lib/utils'
import { camerasApi, eventsApi } from '../api'
import { useInvalidateMemories } from '../hooks'
import { fadeUp, stagger } from '../motion'
import { CameraConnectModal } from './CameraConnect'
import { AuthedImage, ErrorBanner, SectionTitle, Skeleton, errorText } from './shared'

const KIND: Record<EventKind, { label: string; icon: typeof Cctv }> = {
  staff_violation: { label: t('Xodim qoidabuzarligi'), icon: UserX },
  child_distress: { label: t("Bola yig'layapti / kayfiyati yo'q"), icon: Frown },
  safety: { label: t('Xavfsizlik'), icon: ShieldAlert },
  other: { label: t('Boshqa'), icon: Cctv },
}

const SEVERITY: Record<EventSeverity, { label: string; tone: BadgeTone }> = {
  info: { label: t("Ma'lumot"), tone: 'neutral' },
  warning: { label: t('Ogohlantirish'), tone: 'warning' },
  critical: { label: t('Jiddiy'), tone: 'danger' },
}

const STATUS_FILTERS: { id: EventStatus | 'all'; label: string }[] = [
  { id: 'new', label: t('Yangi') },
  { id: 'acknowledged', label: t("Ko'rildi") },
  { id: 'dismissed', label: t("Noto'g'ri signal") },
  { id: 'all', label: t('Hammasi') },
]

export function SafetyPanel() {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const invalidate = useInvalidateMemories()
  const [status, setStatus] = useState<EventStatus | 'all'>('new')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const params = status === 'all' ? { page_size: 50 } : { status, page_size: 50 }
  const events = useQuery({
    queryKey: queryKeys.cameraEvents(organizationId, params),
    queryFn: () => eventsApi.list(params),
    refetchInterval: 15_000,
  })
  const cameras = useQuery({ queryKey: queryKeys.cameras(organizationId), queryFn: camerasApi.list })

  const onError = (err: unknown) => setError(errorText(err))
  const ack = useMutation({
    mutationFn: eventsApi.acknowledge,
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError,
  })
  const dismiss = useMutation({
    mutationFn: eventsApi.dismiss,
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError,
  })

  const rows = events.data?.items ?? []

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <SectionTitle
          title={t('Hodisalar')}
          hint={t("Kamera tahlilchisi aniqlagan holatlar. Jiddiylari rahbarga Telegram'da ham boradi.")}
        >
          {can('memories.create') && (
            <Button variant="outline" icon={Plus} onClick={() => setOpen(true)}>
              {t("Hodisa qo'shish")}
            </Button>
          )}
        </SectionTitle>

        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setStatus(f.id)}
              className={cn(
                'rounded-full border px-3 py-1 text-sm font-medium transition-colors',
                status === f.id
                  ? 'border-brand-600 bg-brand-50 text-brand-700'
                  : 'border-slate-200 text-slate-600 hover:bg-slate-50',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        <ErrorBanner message={error} />

        {events.isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <Card>
            <EmptyState
              icon={CheckCheck}
              title={t('Hodisa yo‘q')}
              hint={t("Hammasi tinch. Yangi hodisa paydo bo'lsa, shu yerda ko'rinadi.")}
            />
          </Card>
        ) : (
          <motion.ul variants={stagger()} initial="hidden" animate="show" className="space-y-3">
            <AnimatePresence initial={false}>
              {rows.map((event) => (
                <EventRow
                  key={event.id}
                  event={event}
                  canEdit={can('memories.update')}
                  busy={ack.isPending || dismiss.isPending}
                  onAck={() => ack.mutate(event.id)}
                  onDismiss={() => dismiss.mutate(event.id)}
                />
              ))}
            </AnimatePresence>
          </motion.ul>
        )}
      </section>

      <CamerasSection cameras={cameras.data?.items ?? []} loading={cameras.isLoading} />

      <EventModal
        open={open}
        onClose={() => setOpen(false)}
        cameras={cameras.data?.items ?? []}
        onDone={invalidate}
      />
    </div>
  )
}

function EventRow({
  event,
  canEdit,
  busy,
  onAck,
  onDismiss,
}: {
  event: CameraEvent
  canEdit: boolean
  busy: boolean
  onAck: () => void
  onDismiss: () => void
}) {
  const kind = KIND[event.kind]
  const severity = SEVERITY[event.severity]
  const Icon = kind.icon
  return (
    <motion.li variants={fadeUp} layout exit={{ opacity: 0, scale: 0.97 }}>
      <Card
        className={cn(
          'flex flex-col gap-4 p-4 sm:flex-row',
          event.severity === 'critical' && event.status === 'new' && 'border-red-200 bg-red-50/30',
        )}
      >
        {event.snapshot_url && (
          <AuthedImage
            path={eventsApi.snapshotPath(event.id)}
            alt={kind.label}
            className="h-32 w-full shrink-0 rounded-xl object-cover sm:w-48"
          />
        )}
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-100 text-slate-600">
              <Icon className="h-4 w-4" />
            </span>
            <span className="text-sm font-semibold text-slate-900">{kind.label}</span>
            <Badge tone={severity.tone}>{severity.label}</Badge>
            {event.alerted_at && <Badge tone="info">{t('Rahbarga yuborilgan')}</Badge>}
          </div>
          {event.note && <p className="text-sm text-slate-700">{event.note}</p>}
          <p className="text-xs text-slate-400">
            {event.camera_name ? `${event.camera_name} · ` : ''}
            {formatDateTime(event.occurred_at)}
          </p>
          {canEdit && event.status === 'new' && (
            <div className="flex flex-wrap gap-2 pt-1">
              <Button icon={CheckCheck} disabled={busy} onClick={onAck} className="px-3 py-1.5">
                {t("Ko'rildi")}
              </Button>
              <Button
                variant="outline"
                icon={XCircle}
                disabled={busy}
                onClick={onDismiss}
                className="px-3 py-1.5"
              >
                {t("Noto'g'ri signal")}
              </Button>
            </div>
          )}
        </div>
      </Card>
    </motion.li>
  )
}

function CamerasSection({
  cameras,
  loading,
}: {
  cameras: Camera[]
  loading: boolean
}) {
  const { can } = useCan()
  const invalidate = useInvalidateMemories()
  const [name, setName] = useState('')
  const [location, setLocation] = useState('')
  const [url, setUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [connectId, setConnectId] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () =>
      camerasApi.create({ name: name.trim(), location: location.trim(), stream_url: url.trim() }),
    onSuccess: () => {
      setName('')
      setLocation('')
      setUrl('')
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorText(err)),
  })
  const remove = useMutation({
    mutationFn: camerasApi.remove,
    onSuccess: invalidate,
    onError: (err) => setError(errorText(err)),
  })

  return (
    <section className="space-y-4">
      <SectionTitle
        title={t('Kameralar')}
        hint={t("Oqim manzili shifrlanib saqlanadi va bu yerda qayta ko'rsatilmaydi.")}
      />
      <ErrorBanner message={error} />
      {loading ? (
        <Skeleton className="h-20" />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cameras.map((cam) => (
            <li key={cam.id}>
              <Card className="flex items-center gap-3 p-4">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-ildiz-50 text-ildiz-700">
                  <Cctv className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-900">{cam.name}</p>
                  <p className="truncate text-xs text-slate-500">
                    {cam.location || t('Joylashuv ko‘rsatilmagan')}
                  </p>
                </div>
                <Badge tone={cam.is_online ? 'success' : cam.has_token ? 'warning' : 'neutral'}>
                  {cam.is_online ? t('Onlayn') : cam.has_token ? t('Oflayn') : t('Ulanmagan')}
                </Badge>
                <button
                  type="button"
                  aria-label={t('Kamerani ulash')}
                  onClick={() => setConnectId(cam.id)}
                  className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-brand-50 hover:text-brand-700"
                >
                  <Link2 className="h-4 w-4" />
                </button>
                {can('memories.delete') && (
                  <button
                    type="button"
                    aria-label={t("O'chirish")}
                    onClick={() => remove.mutate(cam.id)}
                    className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
      {can('memories.create') && (
        <Card className="grid gap-3 p-4 sm:grid-cols-4">
          <Field label={t('Nomi')}>
            <TextInput value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t('Joylashuvi')}>
            <TextInput
              value={location}
              maxLength={120}
              onChange={(e) => setLocation(e.target.value)}
            />
          </Field>
          <Field label={t('Oqim manzili')} hint="rtsp://…">
            <TextInput
              value={url}
              maxLength={500}
              autoComplete="off"
              onChange={(e) => setUrl(e.target.value)}
            />
          </Field>
          <div className="flex items-end">
            <Button
              icon={Plus}
              disabled={!name.trim() || create.isPending}
              onClick={() => create.mutate()}
              className="w-full"
            >
              {t("Kamera qo'shish")}
            </Button>
          </div>
        </Card>
      )}
      <CameraConnectModal
        key={connectId ?? 'none'}
        camera={cameras.find((c) => c.id === connectId) ?? null}
        canEdit={can('memories.update')}
        onClose={() => setConnectId(null)}
      />
    </section>
  )
}

function EventModal({
  open,
  onClose,
  cameras,
  onDone,
}: {
  open: boolean
  onClose: () => void
  cameras: { id: string; name: string }[]
  onDone: () => void
}) {
  const { toast } = useToast()
  const fileRef = useRef<HTMLInputElement>(null)
  const [kind, setKind] = useState<EventKind>('staff_violation')
  const [severity, setSeverity] = useState<EventSeverity>('warning')
  const [camera, setCamera] = useState('')
  const [note, setNote] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () =>
      eventsApi.create({
        kind,
        severity,
        note: note.trim(),
        camera_id: camera || undefined,
        snapshot: file ?? undefined,
      }),
    onSuccess: () => {
      toast(t('Hodisa qayd etildi.'))
      setNote('')
      setFile(null)
      setError(null)
      onDone()
      onClose()
    },
    onError: (err) => setError(errorText(err)),
  })

  return (
    <Modal open={open} onClose={onClose}>
      <div className="space-y-4 p-6">
        <h3 className="pr-8 text-lg font-semibold text-slate-900">{t("Hodisa qo'shish")}</h3>
        <ErrorBanner message={error} />
        <Select
          label={t('Turi')}
          value={kind}
          onChange={(v) => setKind(v as EventKind)}
          options={(Object.keys(KIND) as EventKind[]).map((k) => ({ value: k, label: KIND[k].label }))}
        />
        <Select
          label={t('Daraja')}
          value={severity}
          onChange={(v) => setSeverity(v as EventSeverity)}
          options={(Object.keys(SEVERITY) as EventSeverity[]).map((k) => ({
            value: k,
            label: SEVERITY[k].label,
          }))}
        />
        {cameras.length > 0 && (
          <Select
            label={t('Kamera')}
            placeholder={t('Kamerani tanlang')}
            value={camera}
            onChange={setCamera}
            options={cameras.map((c) => ({ value: c.id, label: c.name }))}
          />
        )}
        <Field label={t('Izoh')}>
          <TextInput value={note} maxLength={400} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <Button variant="outline" onClick={() => fileRef.current?.click()}>
          {file ? file.name : t('Rasm dalilini tanlash')}
        </Button>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t('Bekor qilish')}
          </Button>
          <Button disabled={create.isPending} onClick={() => create.mutate()}>
            {t('Saqlash')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default SafetyPanel
