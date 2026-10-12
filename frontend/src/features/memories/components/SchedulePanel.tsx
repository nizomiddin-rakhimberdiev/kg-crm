/**
 * Kun tartibi: menyu, ovqat vaqti, mashg'ulot.
 * `notify` yoqilgan element belgilangan vaqtda ota-onalarning Telegram botiga ketadi.
 */

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { BellRing, Palette, Plus, Trash2, UtensilsCrossed, Soup } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { Badge, Button, Card, Select, Switch } from '@/components/ui/primitives'
import { EmptyState } from '@/components/ui/EmptyState'
import { Field, TextInput } from '@/components/ui/form'
import { Modal } from '@/components/ui/Modal'
import { queryKeys } from '@/lib/api/queryKeys'
import type { ScheduleItem, ScheduleKind } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { scheduleApi } from '../api'
import { useInvalidateMemories } from '../hooks'
import { fadeUp, stagger } from '../motion'
import { ErrorBanner, SectionTitle, Skeleton, errorText } from './shared'

const KINDS: Record<ScheduleKind, { label: string; icon: typeof Soup; tone: string }> = {
  menu: { label: t('Menyu'), icon: Soup, tone: 'bg-orik-50 text-orik-700' },
  meal: { label: t('Ovqat'), icon: UtensilsCrossed, tone: 'bg-nihol-50 text-nihol-700' },
  activity: { label: t("Mashg'ulot"), icon: Palette, tone: 'bg-brand-50 text-brand-700' },
}

const today = () => new Date().toLocaleDateString('sv-SE') // YYYY-MM-DD, mahalliy vaqt

export function SchedulePanel() {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const { toast } = useToast()
  const invalidate = useInvalidateMemories()
  const [date, setDate] = useState(today)
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const query = useQuery({
    queryKey: queryKeys.scheduleItems(organizationId, date),
    queryFn: () => scheduleApi.list(date),
  })
  const items = query.data?.items ?? []

  const remove = useMutation({
    mutationFn: scheduleApi.remove,
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorText(err)),
  })

  return (
    <div className="space-y-4">
      <SectionTitle
        title={t('Kun tartibi')}
        hint={t("Ota-onalar Telegram'da bugungi menyu va mashg'ulotlarni shu yerdan oladi.")}
      >
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value || today())}
          aria-label={t('Sana')}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
        />
        {can('memories.create') && (
          <Button icon={Plus} onClick={() => setOpen(true)}>
            {t("Qo'shish")}
          </Button>
        )}
      </SectionTitle>

      <ErrorBanner message={error} />

      {query.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={Soup}
            title={t("Bu kun uchun reja yo'q")}
            hint={t("Menyu yoki mashg'ulot qo'shing — ota-onaga o'z vaqtida yuboriladi.")}
          />
        </Card>
      ) : (
        <motion.ul variants={stagger()} initial="hidden" animate="show" className="space-y-2">
          <AnimatePresence initial={false}>
            {items.map((item) => (
              <ScheduleRow
                key={item.id}
                item={item}
                canDelete={can('memories.delete')}
                onDelete={() => remove.mutate(item.id)}
              />
            ))}
          </AnimatePresence>
        </motion.ul>
      )}

      <AddModal
        open={open}
        date={date}
        onClose={() => setOpen(false)}
        onDone={() => {
          toast(t("Kun tartibiga qo'shildi."))
          invalidate()
        }}
      />
    </div>
  )
}

function ScheduleRow({
  item,
  canDelete,
  onDelete,
}: {
  item: ScheduleItem
  canDelete: boolean
  onDelete: () => void
}) {
  const kind = KINDS[item.kind]
  const Icon = kind.icon
  return (
    <motion.li variants={fadeUp} layout exit={{ opacity: 0, x: -16 }}>
      <Card className="flex items-center gap-3 p-4">
        <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${kind.tone}`}>
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">
            {item.at_time && <span className="mr-2 text-slate-400">{item.at_time.slice(0, 5)}</span>}
            {item.title}
          </p>
          <p className="truncate text-xs text-slate-500">
            {kind.label}
            {item.details ? ` · ${item.details}` : ''}
          </p>
        </div>
        {item.notified_at ? (
          <Badge tone="success">{t('Yuborilgan')}</Badge>
        ) : item.notify ? (
          <Badge tone="info">
            <BellRing className="mr-1 h-3 w-3" />
            {t('Yuboriladi')}
          </Badge>
        ) : null}
        {canDelete && (
          <button
            type="button"
            onClick={onDelete}
            aria-label={t("O'chirish")}
            className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </Card>
    </motion.li>
  )
}

function AddModal({
  open,
  date,
  onClose,
  onDone,
}: {
  open: boolean
  date: string
  onClose: () => void
  onDone: () => void
}) {
  const [kind, setKind] = useState<ScheduleKind>('menu')
  const [time, setTime] = useState('')
  const [title, setTitle] = useState('')
  const [details, setDetails] = useState('')
  const [notify, setNotify] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () =>
      scheduleApi.create({
        kind,
        on_date: date,
        at_time: time || null,
        title: title.trim(),
        details: details.trim(),
        notify,
      }),
    onSuccess: () => {
      setTitle('')
      setDetails('')
      setTime('')
      setError(null)
      onDone()
      onClose()
    },
    onError: (err) => setError(errorText(err)),
  })

  return (
    <Modal open={open} onClose={onClose}>
      <div className="space-y-4 p-6">
        <h3 className="pr-8 text-lg font-semibold text-slate-900">{t("Kun tartibiga qo'shish")}</h3>
        <ErrorBanner message={error} />
        <Select
          label={t('Turi')}
          value={kind}
          onChange={(v) => setKind(v as ScheduleKind)}
          options={(Object.keys(KINDS) as ScheduleKind[]).map((k) => ({
            value: k,
            label: KINDS[k].label,
          }))}
        />
        <Field label={t('Nomi')}>
          <TextInput
            value={title}
            maxLength={160}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t("Masalan: Mastava, rasm chizish")}
          />
        </Field>
        <Field label={t('Vaqti')} hint={t("Bo'sh qolsa, ertalab 08:00 da yuboriladi.")}>
          <TextInput type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </Field>
        <Field label={t("Qo'shimcha")}>
          <TextInput
            value={details}
            maxLength={500}
            onChange={(e) => setDetails(e.target.value)}
            placeholder={t("Masalan: non va qatiq bilan")}
          />
        </Field>
        <Switch checked={notify} onChange={setNotify} label={t("Ota-onaga Telegram'da yuborish")} />
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t('Bekor qilish')}
          </Button>
          <Button disabled={!title.trim() || create.isPending} onClick={() => create.mutate()}>
            {t('Saqlash')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default SchedulePanel
