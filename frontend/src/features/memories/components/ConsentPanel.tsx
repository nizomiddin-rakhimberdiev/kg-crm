/**
 * Yuz roziligi (biometrik ma'lumot).
 *
 * Yuz vektori faqat vasiyning roziligi bo'lgan bola uchun yaratiladi.
 * Rozilik bekor qilinsa, bolaning barcha vektorlari o'sha zahoti o'chadi.
 */

import { useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Camera, ShieldCheck, ShieldOff, UserPlus } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { Badge, Button, Card, Select } from '@/components/ui/primitives'
import { EmptyState } from '@/components/ui/EmptyState'
import { Field, SearchInput } from '@/components/ui/form'
import { Modal } from '@/components/ui/Modal'
import { childrenApi } from '@/features/children/api'
import { queryKeys } from '@/lib/api/queryKeys'
import type { FaceConsent } from '@/lib/api/types'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { formatDate } from '@/lib/utils'
import { consentsApi } from '../api'
import { useInvalidateMemories } from '../hooks'
import { fadeUp, stagger } from '../motion'
import { ErrorBanner, SectionTitle, Skeleton, errorText } from './shared'

export function ConsentPanel() {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const { toast } = useToast()
  const invalidate = useInvalidateMemories()
  const fileRef = useRef<HTMLInputElement>(null)
  const [enrollFor, setEnrollFor] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const query = useQuery({
    queryKey: queryKeys.faceConsents(organizationId),
    queryFn: consentsApi.list,
  })
  const items = query.data?.items ?? []

  const onError = (err: unknown) => setError(errorText(err))
  const revoke = useMutation({
    mutationFn: consentsApi.revoke,
    onSuccess: () => {
      setError(null)
      toast(t("Rozilik bekor qilindi, yuz vektorlari o'chirildi."), 'info')
      invalidate()
    },
    onError,
  })
  const enroll = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => consentsApi.enroll(id, file),
    onSuccess: () => {
      setError(null)
      toast(t('Yuz namunasi saqlandi.'))
      invalidate()
    },
    onError,
  })

  return (
    <div className="space-y-4">
      <SectionTitle
        title={t('Yuz roziligi')}
        hint={t("Vasiyning roziligisiz bolaning yuzi tanilmaydi va vektori saqlanmaydi.")}
      >
        {can('memories.create') && (
          <Button icon={UserPlus} onClick={() => setOpen(true)}>
            {t('Rozilik kiritish')}
          </Button>
        )}
      </SectionTitle>

      <ErrorBanner message={error} />

      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file && enrollFor) enroll.mutate({ id: enrollFor, file })
          e.target.value = ''
        }}
      />

      {query.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={ShieldCheck}
            title={t("Hali rozilik kiritilmagan")}
            hint={t("Rozilik kiritilgach, bolaning 2–3 ta aniq rasmini qo'shing.")}
          />
        </Card>
      ) : (
        <motion.ul variants={stagger()} initial="hidden" animate="show" className="space-y-2">
          {items.map((c) => (
            <ConsentRow
              key={c.id}
              consent={c}
              canEdit={can('memories.update')}
              canCreate={can('memories.create')}
              busy={revoke.isPending || enroll.isPending}
              onEnroll={() => {
                setEnrollFor(c.id)
                fileRef.current?.click()
              }}
              onRevoke={() => revoke.mutate(c.id)}
            />
          ))}
        </motion.ul>
      )}

      <GrantModal open={open} onClose={() => setOpen(false)} onDone={invalidate} />
    </div>
  )
}

function ConsentRow({
  consent,
  canEdit,
  canCreate,
  busy,
  onEnroll,
  onRevoke,
}: {
  consent: FaceConsent
  canEdit: boolean
  canCreate: boolean
  busy: boolean
  onEnroll: () => void
  onRevoke: () => void
}) {
  const active = !consent.revoked_at
  return (
    <motion.li variants={fadeUp} layout>
      <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">{consent.child_name}</p>
          <p className="truncate text-xs text-slate-500">
            {t('Vasiy: {name}', { name: consent.guardian_name })} · {formatDate(consent.given_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {active ? (
            <Badge tone="success">{t('Rozilik bor')}</Badge>
          ) : (
            <Badge tone="neutral">{t('Bekor qilingan')}</Badge>
          )}
          <Badge tone={consent.samples > 0 ? 'info' : 'warning'}>
            {t('{count} ta namuna', { count: consent.samples })}
          </Badge>
          {active && canCreate && (
            <Button variant="outline" icon={Camera} disabled={busy} onClick={onEnroll}>
              {t("Yuz qo'shish")}
            </Button>
          )}
          {active && canEdit && (
            <Button
              variant="ghost"
              icon={ShieldOff}
              disabled={busy}
              className="text-red-600 hover:bg-red-50"
              onClick={onRevoke}
            >
              {t('Bekor qilish')}
            </Button>
          )}
        </div>
      </Card>
    </motion.li>
  )
}

function GrantModal({
  open,
  onClose,
  onDone,
}: {
  open: boolean
  onClose: () => void
  onDone: () => void
}) {
  const { toast } = useToast()
  const [search, setSearch] = useState('')
  const debounced = useDebouncedValue(search, 250)
  const [childId, setChildId] = useState('')
  const [guardianId, setGuardianId] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const organizationId = useOrganizationId()

  const children = useQuery({
    queryKey: queryKeys.children(organizationId, { search: debounced, page_size: 20 }),
    queryFn: () => childrenApi.list({ search: debounced, page_size: 20 }),
    enabled: open,
  })
  const list = children.data?.items ?? []
  const child = list.find((c) => c.id === childId)

  const grant = useMutation({
    mutationFn: () => consentsApi.grant(childId, guardianId),
    onSuccess: () => {
      toast(t('Rozilik saqlandi.'))
      onDone()
      reset()
      onClose()
    },
    onError: (err) => setError(errorText(err)),
  })

  const reset = () => {
    setChildId('')
    setGuardianId('')
    setConfirmed(false)
    setError(null)
    setSearch('')
  }

  return (
    <Modal open={open} onClose={onClose}>
      <div className="space-y-4 p-6">
        <h3 className="pr-8 text-lg font-semibold text-slate-900">{t('Yuz roziligini kiritish')}</h3>
        <ErrorBanner message={error} />
        <Field label={t('Bolani qidiring')}>
          <SearchInput value={search} onChange={setSearch} placeholder={t('Ism yoki familiya')} />
        </Field>
        <Select
          label={t('Bola')}
          placeholder={t('Bolani tanlang')}
          value={childId}
          onChange={(v) => {
            setChildId(v)
            setGuardianId('')
          }}
          options={list.map((c) => ({ value: c.id, label: c.full_name }))}
        />
        {child && (
          <Select
            label={t('Rozilik bergan vasiy')}
            placeholder={t('Vasiyni tanlang')}
            value={guardianId}
            onChange={setGuardianId}
            options={child.guardians.map((g) => ({
              value: g.guardian.id,
              label: `${g.guardian.full_name} · ${g.guardian.phone}`,
            }))}
          />
        )}
        <label className="flex items-start gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300"
          />
          <span>
            {t("Vasiyning bola yuzini tanishga yozma roziligi olingan va arxivda saqlanadi.")}
          </span>
        </label>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t('Bekor qilish')}
          </Button>
          <Button
            disabled={!childId || !guardianId || !confirmed || grant.isPending}
            onClick={() => grant.mutate()}
          >
            {t('Saqlash')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ConsentPanel
