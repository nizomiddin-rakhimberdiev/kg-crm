/**
 * Kamerani Radix'ga ulash oynasi: uch yo'l, bitta token modeli.
 *
 *  1. Bog'cha kompyuteri (RTSP) — dastur kamerani ichki tarmoqda o'qiydi.
 *  2. NVR / ko'p kamera (ONVIF) — bitta dastur bir nechta kanalni yuboradi.
 *  3. Webhook — NVR yoki bulut tizimi hodisani o'zi yuboradi.
 *
 * Token FAQAT bir marta ko'rsatiladi (serverda xesh saqlanadi). Oyna yopilsa
 * token xotiradan o'chadi. Kuzatuv (so'nggi kadr) alohida, ONGLI yoqiladi:
 * bolalar tasviri bo'lgani uchun u standart o'chiq.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Check, Copy, KeyRound, ShieldOff } from 'lucide-react'
import { Badge, Button, Switch } from '@/components/ui/primitives'
import { Modal } from '@/components/ui/Modal'
import { env } from '@/config/env'
import type { Camera } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { cn, formatDateTime } from '@/lib/utils'
import { camerasApi } from '../api'
import { useInvalidateMemories } from '../hooks'
import { ErrorBanner, errorText } from './shared'

type Method = 'edge' | 'nvr' | 'webhook'

const METHODS: { id: Method; label: string; hint: string }[] = [
  {
    id: 'edge',
    label: t('Bog‘cha kompyuteri (RTSP)'),
    hint: t('Bitta kamera. Dastur kamerani bog‘cha tarmog‘ida o‘qiydi.'),
  },
  {
    id: 'nvr',
    label: t('NVR / ko‘p kamera (ONVIF)'),
    hint: t('Bir dastur bir nechta kanalni yuboradi; oqimlarni o‘zi topadi.'),
  },
  {
    id: 'webhook',
    label: t('Webhook (NVR / bulut)'),
    hint: t('NVR yoki bulut tizimi hodisani o‘zi yuboradi.'),
  },
]

function CopyBox({ value, label }: { value: string; label: string }) {
  const [done, setDone] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setDone(true)
      window.setTimeout(() => setDone(false), 2000)
    } catch {
      /* clipboard bloklangan — foydalanuvchi qo'lda belgilab oladi */
    }
  }
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <div className="flex items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2.5">
        <code className="min-w-0 flex-1 select-all whitespace-pre-wrap break-all font-mono text-xs leading-5 text-slate-800">
          {value}
        </code>
        <button
          type="button"
          onClick={() => void copy()}
          aria-label={t('Nusxalash')}
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-500 transition-colors hover:bg-white hover:text-brand-700"
        >
          {done ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
        </button>
      </div>
    </div>
  )
}

function apiBase(): string {
  return env.apiBaseUrl.startsWith('http')
    ? env.apiBaseUrl
    : `${window.location.origin}${env.apiBaseUrl}`
}

function instructions(method: Method, token: string): { label: string; text: string }[] {
  const base = apiBase()
  if (method === 'webhook') {
    return [
      {
        label: t('Manzil (sarlavha qo‘llanadigan tizimlar uchun — afzal)'),
        text: `POST ${base}/camera-webhook\nAuthorization: Bearer ${token}`,
      },
      {
        label: t('Manzil (faqat sarlavha sozlab bo‘lmaydigan NVR uchun)'),
        text: `${base}/camera-webhook/${token}`,
      },
    ]
  }
  if (method === 'nvr') {
    return [
      {
        label: t('1. Oqimlarni toping (ONVIF)'),
        text: `python -m edge.camera_worker --onvif NVR_IP`,
      },
      {
        label: t('2. Sozlama faylidagi shu kamera qatori'),
        text: `{ "name": "${t('Kamera')}", "token": "${token}", "rtsp": "rtsp://LOGIN:PAROL@NVR_IP:554/..." }`,
      },
      {
        label: t('3. Hammasini ishga tushiring'),
        text: `python -m edge.camera_worker --config cameras.json`,
      },
    ]
  }
  return [
    {
      label: t('Bog‘cha kompyuterida ishga tushiring'),
      text: `$env:RADIX_SERVER="${base}"\n$env:RADIX_CAMERA_TOKEN="${token}"\n$env:RADIX_RTSP_URL="rtsp://LOGIN:PAROL@KAMERA_IP:554/stream1"\npython -m edge.camera_worker --test`,
    },
  ]
}

export function CameraConnectModal({
  camera,
  canEdit,
  onClose,
}: {
  camera: Camera | null
  canEdit: boolean
  onClose: () => void
}) {
  const invalidate = useInvalidateMemories()
  const [method, setMethod] = useState<Method>(camera?.connection === 'webhook' ? 'webhook' : 'edge')
  const [token, setToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const close = () => {
    setToken(null)
    setError(null)
    onClose()
  }

  const issue = useMutation({
    mutationFn: () => camerasApi.issueToken(camera!.id, method === 'webhook' ? 'webhook' : 'edge'),
    onSuccess: (data) => {
      setToken(data.token)
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorText(err)),
  })
  const revoke = useMutation({
    mutationFn: () => camerasApi.revokeToken(camera!.id),
    onSuccess: () => {
      setToken(null)
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorText(err)),
  })
  const preview = useMutation({
    mutationFn: (enabled: boolean) => camerasApi.setPreview(camera!.id, enabled),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorText(err)),
  })

  return (
    <Modal open={camera !== null} onClose={close}>
      {camera && (
        <div className="max-h-[85vh] space-y-4 overflow-y-auto p-6">
          <div className="pr-8">
            <h3 className="text-lg font-semibold text-slate-900">{t('Kamerani ulash')}</h3>
            <p className="mt-0.5 text-sm text-slate-500">{camera.name}</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={camera.is_online ? 'success' : 'neutral'}>
              {camera.is_online ? t('Onlayn') : t('Oflayn')}
            </Badge>
            <span className="text-xs text-slate-500">
              {camera.last_seen_at
                ? `${t('Oxirgi signal')}: ${formatDateTime(camera.last_seen_at)}`
                : t('Hali signal kelmagan')}
            </span>
          </div>

          <ErrorBanner message={error} />

          {!token && (
            <div role="radiogroup" aria-label={t('Ulanish usuli')} className="grid gap-2">
              {METHODS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  role="radio"
                  aria-checked={method === m.id}
                  onClick={() => setMethod(m.id)}
                  className={cn(
                    'rounded-xl border px-3.5 py-2.5 text-left transition-colors',
                    method === m.id
                      ? 'border-brand-600 bg-brand-50'
                      : 'border-slate-200 hover:bg-slate-50',
                  )}
                >
                  <span className="block text-sm font-semibold text-slate-900">{m.label}</span>
                  <span className="block text-xs text-slate-500">{m.hint}</span>
                </button>
              ))}
              <p className="text-xs leading-5 text-slate-500">
                {t(
                  'Bulutli kameralar (Hik-Connect, EZVIZ, Tapo) odatda RTSP bermaydi: ilovasida RTSP/ONVIF ni yoqing yoki tizim HTTP xabarnoma yuborsa, webhook’dan foydalaning.',
                )}
              </p>
            </div>
          )}

          {token ? (
            <div className="space-y-3">
              <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                {t('Tokenni hozir nusxalang — u boshqa ko‘rsatilmaydi.')}
              </p>
              <CopyBox value={token} label={t('Ulanish tokeni')} />
              {instructions(method, token).map((item) => (
                <CopyBox key={item.label} value={item.text} label={item.label} />
              ))}
              {method === 'webhook' ? (
                <p className="text-xs leading-5 text-amber-700">
                  {t(
                    'URL ichidagi token NVR va proksi loglarida qoladi: shuning uchun u faqat hodisa yozadi, kuzatuv kadrini emas. Imkon bo‘lsa sarlavhali usulni tanlang.',
                  )}
                </p>
              ) : (
                <p className="text-xs leading-5 text-slate-500">
                  {t(
                    "Kamera paroli Radix'ga yuborilmaydi: dastur uni bog'cha tarmog'ida o'zi o'qiydi va faqat signal hamda rasm yuboradi.",
                  )}
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm leading-6 text-slate-600">
              {camera.has_token
                ? t("Kamera ulangan. Yangi token berilsa, eskisi darhol bekor bo'ladi.")
                : t('Kamerani ulash uchun token bering va uni bog‘cha kompyuteridagi dasturga kiriting.')}
            </p>
          )}

          {canEdit && method !== 'webhook' && (
            <div className="flex items-start justify-between gap-4 rounded-xl border border-slate-200 p-3.5">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">
                  {t('Kuzatuv: so‘nggi kadrni ko‘rsatish')}
                </p>
                <p className="mt-0.5 text-xs leading-5 text-slate-500">
                  {t(
                    'Yoqilsa, kamera har necha soniyada bitta kadr yuboradi va faqat so‘nggisi saqlanadi. Rahbarlar ko‘ra oladi. O‘chirilsa, kadr darhol o‘chadi.',
                  )}
                </p>
              </div>
              <Switch
                checked={camera.preview_enabled}
                disabled={preview.isPending}
                onChange={(value) => preview.mutate(value)}
                label={t('Kuzatuv: so‘nggi kadrni ko‘rsatish')}
              />
            </div>
          )}

          <div className="flex flex-wrap justify-end gap-2">
            {canEdit && camera.has_token && !token && (
              <Button
                variant="outline"
                icon={ShieldOff}
                disabled={revoke.isPending}
                onClick={() => revoke.mutate()}
              >
                {t('Tokenni bekor qilish')}
              </Button>
            )}
            {canEdit && !token && (
              <Button icon={KeyRound} disabled={issue.isPending} onClick={() => issue.mutate()}>
                {camera.has_token ? t('Yangi token berish') : t('Token berish')}
              </Button>
            )}
            <Button variant="outline" onClick={close}>
              {t('Yopish')}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}
