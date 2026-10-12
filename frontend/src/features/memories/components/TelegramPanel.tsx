/**
 * Telegram: guruh, ota-onalar va rahbar chatlarini ulash.
 *
 * Ulash havolasi bir martalik va 48 soat amal qiladi; backend uning faqat
 * xeshini saqlaydi. Havola — kalit: uni faqat egasiga yuboring.
 */

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, Copy, ExternalLink, Link2, Send, Trash2, UserRound, Users } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { Badge, Button, Card, Select } from '@/components/ui/primitives'
import { EmptyState } from '@/components/ui/EmptyState'
import { SearchInput } from '@/components/ui/form'
import { childrenApi } from '@/features/children/api'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { queryKeys } from '@/lib/api/queryKeys'
import type { ChatKind, PairingLink, TelegramChat } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { formatDate } from '@/lib/utils'
import { telegramApi } from '../api'
import { useInvalidateMemories } from '../hooks'
import { fadeUp, stagger } from '../motion'
import { ErrorBanner, SectionTitle, Skeleton, errorText } from './shared'

const KIND_LABEL: Record<ChatKind, string> = {
  group: t("Bog'cha guruhi"),
  parent: t('Ota-ona'),
  staff: t('Rahbar'),
}

export function TelegramPanel() {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const invalidate = useInvalidateMemories()
  const [link, setLink] = useState<{ kind: ChatKind; value: PairingLink } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const chats = useQuery({
    queryKey: queryKeys.telegramChats(organizationId),
    queryFn: telegramApi.list,
  })

  const pair = useMutation({
    mutationFn: ({ kind, guardianId }: { kind: ChatKind; guardianId?: string }) =>
      telegramApi.pairing(kind, guardianId).then((value) => ({ kind, value })),
    onSuccess: (result) => {
      setError(null)
      setLink(result)
    },
    onError: (err) => setError(errorText(err)),
  })
  const remove = useMutation({
    mutationFn: telegramApi.remove,
    onSuccess: invalidate,
    onError: (err) => setError(errorText(err)),
  })

  const items = chats.data?.items ?? []

  return (
    <div className="space-y-6">
      <SectionTitle
        title={t('Telegram bot')}
        hint={t("Ota-onalar rasmlar, menyu va kun tartibini shu bot orqali oladi.")}
      />
      <ErrorBanner message={error} />

      {can('memories.create') && (
        <div className="grid gap-3 md:grid-cols-2">
          <Card className="space-y-3 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Users className="h-4 w-4 text-brand-600" />
              {t("Bog'cha guruhini ulash")}
            </div>
            <p className="text-sm text-slate-500">
              {t("Botni o'qituvchilar guruhiga qo'shing va havola orqali ulang.")}
            </p>
            <Button
              icon={Link2}
              disabled={pair.isPending}
              onClick={() => pair.mutate({ kind: 'group' })}
            >
              {t('Havola yaratish')}
            </Button>
          </Card>
          <Card className="space-y-3 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Send className="h-4 w-4 text-brand-600" />
              {t('Rahbar ogohlantirishlari')}
            </div>
            <p className="text-sm text-slate-500">
              {t("Kamera hodisalari rasm dalili bilan shu Telegram'ga keladi.")}
            </p>
            <Button
              variant="outline"
              icon={Link2}
              disabled={pair.isPending}
              onClick={() => pair.mutate({ kind: 'staff' })}
            >
              {t("O'zim uchun havola")}
            </Button>
          </Card>
          <ParentPairing
            busy={pair.isPending}
            onPair={(guardianId) => pair.mutate({ kind: 'parent', guardianId })}
          />
        </div>
      )}

      <AnimatePresence>
        {link && <LinkCard key={link.value.url} link={link} onClose={() => setLink(null)} />}
      </AnimatePresence>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-700">{t('Ulangan chatlar')}</h3>
        {chats.isLoading ? (
          <Skeleton className="h-16" />
        ) : items.length === 0 ? (
          <Card>
            <EmptyState
              icon={Send}
              title={t("Hali chat ulanmagan")}
              hint={t("Yuqoridagi havolalardan birini yarating va Telegram'da oching.")}
            />
          </Card>
        ) : (
          <motion.ul variants={stagger()} initial="hidden" animate="show" className="space-y-2">
            {items.map((chat) => (
              <ChatRow
                key={chat.id}
                chat={chat}
                canDelete={can('memories.delete')}
                onDelete={() => remove.mutate(chat.id)}
              />
            ))}
          </motion.ul>
        )}
      </section>
    </div>
  )
}

function ParentPairing({ busy, onPair }: { busy: boolean; onPair: (guardianId: string) => void }) {
  const organizationId = useOrganizationId()
  const [search, setSearch] = useState('')
  const debounced = useDebouncedValue(search, 250)
  const [childId, setChildId] = useState('')
  const [guardianId, setGuardianId] = useState('')

  const children = useQuery({
    queryKey: queryKeys.children(organizationId, { search: debounced, page_size: 20 }),
    queryFn: () => childrenApi.list({ search: debounced, page_size: 20 }),
  })
  const list = children.data?.items ?? []
  const child = list.find((c) => c.id === childId)

  return (
    <Card className="space-y-3 p-4 md:col-span-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <UserRound className="h-4 w-4 text-brand-600" />
        {t('Ota-onani ulash')}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <SearchInput value={search} onChange={setSearch} placeholder={t('Bolani qidiring')} />
        <Select
          placeholder={t('Bolani tanlang')}
          value={childId}
          onChange={(v) => {
            setChildId(v)
            setGuardianId('')
          }}
          options={list.map((c) => ({ value: c.id, label: c.full_name }))}
        />
        <Select
          placeholder={t('Vasiyni tanlang')}
          value={guardianId}
          onChange={setGuardianId}
          options={(child?.guardians ?? []).map((g) => ({
            value: g.guardian.id,
            label: g.guardian.full_name,
          }))}
        />
      </div>
      <Button icon={Link2} disabled={!guardianId || busy} onClick={() => onPair(guardianId)}>
        {t('Havola yaratish')}
      </Button>
    </Card>
  )
}

function LinkCard({ link, onClose }: { link: { kind: ChatKind; value: PairingLink }; onClose: () => void }) {
  const { toast } = useToast()
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link.value.url)
      setCopied(true)
      toast(t('Havola nusxalandi.'))
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      toast(t("Nusxalab bo'lmadi — havolani qo'lda belgilang."), 'error')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10 }}
    >
      <Card className="space-y-3 border-brand-200 bg-brand-50/40 p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-semibold text-slate-900">
            {t('Ulash havolasi: {kind}', { kind: KIND_LABEL[link.kind] })}
          </p>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-500 hover:text-slate-700"
          >
            {t('Yopish')}
          </button>
        </div>
        <code className="block break-all rounded-lg bg-white px-3 py-2 text-xs text-slate-700">
          {link.value.url}
        </code>
        <p className="text-xs text-slate-500">
          {t("Bir marta ishlaydi, {date} gacha amal qiladi.", {
            date: formatDate(link.value.expires_at),
          })}
        </p>
        <div className="flex gap-2">
          <Button icon={copied ? Check : Copy} onClick={() => void copy()}>
            {copied ? t('Nusxalandi') : t('Nusxalash')}
          </Button>
          <a href={link.value.url} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" icon={ExternalLink} type="button">
              {t('Telegramda ochish')}
            </Button>
          </a>
        </div>
      </Card>
    </motion.div>
  )
}

function ChatRow({
  chat,
  canDelete,
  onDelete,
}: {
  chat: TelegramChat
  canDelete: boolean
  onDelete: () => void
}) {
  return (
    <motion.li variants={fadeUp} layout>
      <Card className="flex items-center gap-3 p-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">
            {chat.guardian_name ?? (chat.title || KIND_LABEL[chat.kind])}
          </p>
          <p className="text-xs text-slate-500">{formatDate(chat.created_at)}</p>
        </div>
        <Badge tone={chat.kind === 'group' ? 'ildiz' : chat.kind === 'staff' ? 'orik' : 'info'}>
          {KIND_LABEL[chat.kind]}
        </Badge>
        <Badge tone="neutral">{chat.language.toUpperCase()}</Badge>
        {canDelete && (
          <button
            type="button"
            aria-label={t('Uzish')}
            onClick={onDelete}
            className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </Card>
    </motion.li>
  )
}

export default TelegramPanel
