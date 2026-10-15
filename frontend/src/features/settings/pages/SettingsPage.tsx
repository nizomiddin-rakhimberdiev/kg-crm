/**
 * Sozlamalar (docs/04 §16).
 *
 * Sozlama — kalit va qiymat; uning ortida baza qatori bormi yoki koddagi
 * default ishlayaptimi, foydalanuvchi uchun farqi yo'q. Shuning uchun
 * sahifa HAR DOIM to'liq ro'yxatni ko'rsatadi, faqat o'zgartirilganlarini
 * emas — "bunday sozlama umuman bormi?" degan savol tug'ilmasin.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { Switch } from '@/components/ui/primitives'
import { settingsApi } from '@/features/notifications/api'
import { ContractTemplatesSettings } from '@/features/contracts/components/ContractTemplatesSettings'
import { OnlinePaymentSettings } from '@/features/online-payments/components/OnlinePaymentSettings'
import { TestModeBanner } from '@/features/notifications/components/TestModeBanner'
import { WeekdayPicker } from '@/features/settings/components/WeekdayPicker'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type SettingValue } from '@/lib/api/types'
import { useFeature } from '@/lib/features'
import { useCan } from '@/lib/rbac/useCan'
import { APP_LOCALES, t } from '@/lib/i18n'

interface SettingMeta {
  label: string
  help: string
}

/**
 * Kalitlar ro'yxati backend'da (`DEFAULTS`), bu yerda faqat ularning
 * odamcha nomi. Yangi kalit qo'shilsa u baribir ko'rinadi — shunchaki
 * tarjimasiz, kalitning o'zi bilan.
 */
const META: Record<string, SettingMeta> = {
  'general.default_language': {
    label: t('Bogʻcha tili'),
    help: t('Xodim oʻzi til tanlamagan boʻlsa, tizim shu tilda ochiladi.'),
  },
  'finance.due_day': {
    label: t('Toʻlov muddati (oy kuni)'),
    help: t('Hisob-faktura shu kungacha toʻlanishi kutiladi.'),
  },
  'finance.reminder_day': {
    label: t('Eslatma kuni'),
    help: t('Qarzdorlarga eslatma shu kundan boshlab yuboriladi.'),
  },
  'notifications.sms_enabled': {
    label: t('Xabarnomalar'),
    help: t('Oʻchirilsa hech qanday xabar yuborilmaydi — na Telegram, na SMS.'),
  },
  'notifications.default_channel': {
    label: t('Asosiy kanal'),
    help: t('Telegram bepul; SMS har xabar uchun pul turadi va shlyuz shartnomasini talab qiladi.'),
  },
  'notifications.absence_alert': {
    label: t('Kelmagani haqida xabar'),
    help: t('Bola bugun «kelmadi» deb belgilansa, ota-onaga xabar ketadi. Pulga taʼsir qilmaydi.'),
  },
  'notifications.payment_receipt': {
    label: t('Toʻlov haqida xabar'),
    help: t('Toʻlov qabul qilinganda ota-onaga xabar ketadi.'),
  },
  'notifications.send_from_hour': {
    label: t('Yuborishni boshlash (soat)'),
    help: t('Bundan oldin tayyor boʻlgan xabar navbatda turadi — tungi xabar yuborilmaydi.'),
  },
  'notifications.send_to_hour': {
    label: t('Yuborishni tugatish (soat)'),
    help: t('Shu soatdan keyin xabar yuborilmaydi, ertalab ketadi.'),
  },
  'notifications.debt_reminders_per_day': {
    label: t('Kuniga eslatma soni'),
    help: t('Bir ota-ona kuniga shundan ortiq qarz eslatmasini olmaydi.'),
  },
  'notifications.max_retries': {
    label: t('Qayta urinish soni'),
    help: t('Xato boʻlgan xabar shuncha marta qayta yuboriladi.'),
  },
  'notifications.sms_price': {
    label: t('Bitta SMS boʻlagi narxi'),
    help: t('Taxminiy xarajatni hisoblash uchun — provayder shartnomasidagi narx.'),
  },
  'finance.first_month_mode': {
    label: t('Birinchi oy hisobi'),
    help: t(
      'Oy oʻrtasida kelgan yoki ketgan bola uchun: toʻliq oy, ish kunlari boʻyicha yoki keyingi oydan.',
    ),
  },
  'finance.trial_days': {
    label: t('Sinov muddati (ish kuni)'),
    help: t(
      'Yangi bolaning birinchi shuncha ish kuni bepul. Sinovda ketsa — hech narsa hisoblanmaydi. 0 — sinov yoʻq.',
    ),
  },
  'finance.rounding_step': {
    label: t('Yaxlitlash (soʻm)'),
    help: t(
      'Hisoblangan summa shu qadamgacha yaxlitlanadi: 1 161 905 → 1 162 000. Kunlik stavka emas, natija.',
    ),
  },
  'finance.first_invoice_grace_days': {
    label: t('Birinchi faktura muddati (kun)'),
    help: t(
      'Qabul sanasidan kamida shuncha kun keyin — bola kelgan kuniyoq qarzdor boʻlib qolmasin.',
    ),
  },
  'attendance.teacher_edit_days': {
    label: t('Tarbiyachi necha kun orqaga belgilaydi'),
    help: t('1 = bugun va kecha. Eski kunlarni faqat direktor sabab bilan oʻzgartiradi.'),
  },
  'attendance.working_weekdays': {
    label: t('Ish kunlari'),
    help: t(
      'Kunlik toʻlov shu kunlar boʻyicha hisoblanadi — shanba ishlaydigan bogʻcha uchun ham.',
    ),
  },
  'children.min_age': {
    label: t('Eng kichik yosh'),
    help: t('Bu yoshdan kichik bola qoʻshilmaydi — xato yozilgan tugʻilgan sana shunda ushlanadi.'),
  },
  'children.max_age': {
    label: t('Eng katta yosh'),
    help: t('Bogʻchalar turlicha: baʼzilari 7 yoshgacha oladi.'),
  },
  'payroll.income_tax_rate': {
    label: t('Daromad soligʻi (%)'),
    help: t('Xodim maoshidan ushlanadi. 0 — ushlanmaydi.'),
  },
  'payroll.pension_rate': {
    label: t('Pensiya jamgʻarmasi (%)'),
    help: t('Xodim maoshidan ushlanadi. 0 — ushlanmaydi.'),
  },
  'payroll.social_tax_rate': {
    label: t('Ijtimoiy soliq (%)'),
    help: t('Bogʻcha ustiga toʻlaydi — xodim maoshidan ushlanmaydi.'),
  },
  'attendance.auto_absent': {
    label: t('Avtomatik "kelmadi"'),
    help: t('Belgilanmagan bolalar kun oxirida kelmagan deb yoziladi.'),
  },
  // Shartnoma rekvizitlari (PLAN 9.3) — shablondagi {{...}} maydonlar
  // shu yerdan to'ldiriladi.
  'contracts.director_name': {
    label: t('Direktor (F.I.Sh.)'),
    help: t('Shartnomada imzo qoʻyuvchi shaxs.'),
  },
  'contracts.bank_name': {
    label: t('Bank nomi'),
    help: t('Shartnomaning rekvizitlar qismida koʻrsatiladi.'),
  },
  'contracts.bank_account': {
    label: t('Hisob raqami'),
    help: t('Bogʻchaning hisob-kitob raqami.'),
  },
  'contracts.bank_mfo': { label: t('MFO'), help: t('Bank kodi.') },
  'contracts.daily_meal_fee': {
    label: t('Bir kunlik ovqat puli (soʻm)'),
    help: t('Bola kelmagan kun uchun shartnoma boʻyicha ayriladigan summa.'),
  },
  'contracts.free_absence_days': {
    label: t('Toʻlovsiz saqlanadigan kunlar'),
    help: t('Yiliga shuncha ish kuni joy toʻlovsiz saqlanadi.'),
  },
  'contracts.daily_hours': {
    label: t('Kunlik saqlash vaqti (soat)'),
    help: t('Shartnomaning birinchi bandidagi soat.'),
  },
}

const GROUPS: Array<[string, string]> = [
  ['general', t('Umumiy')],
  ['finance', t('Moliya')],
  ['notifications', t('Bildirishnomalar')],
  ['attendance', t('Davomat')],
  ['contracts', t('Shartnoma rekvizitlari')],
]

export default function SettingsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const editable = can('settings.update')
  const contractsOn = useFeature('contracts')

  const [error, setError] = useState<string | null>(null)
  const [savedKey, setSavedKey] = useState<string | null>(null)
  const { toast } = useToast()

  const settingsQuery = useQuery({
    queryKey: queryKeys.settings(organizationId),
    queryFn: settingsApi.all,
  })

  const save = useMutation({
    mutationFn: ({ key, value }: { key: string; value: SettingValue }) =>
      settingsApi.set(key, value),
    onSuccess: (result) => {
      setError(null)
      setSavedKey(result.key)
      toast(t('Saqlandi'))
      void queryClient.invalidateQueries({ queryKey: queryKeys.settings(organizationId) })
    },
    onError: (err: unknown) =>
      setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.')),
  })

  const settings = settingsQuery.data ?? {}
  const keys = Object.keys(settings).sort()

  const renderControl = (key: string, value: SettingValue) => {
    // Til — ro'yxatdan tanlanadi. Erkin matn maydoni bo'lsa, xato yozilgan
    // kod ("рус") jimgina ishlamay qo'yardi.
    // Ish kunlari — katakchalar (PLAN 4.2). Erkin matnda bitta xato
    // belgi kunlik to'lov hisobini jimgina buzardi (ADR-19).
    if (key === 'attendance.working_weekdays') {
      return (
        <WeekdayPicker
          value={value}
          disabled={!editable || save.isPending}
          onChange={(next) => save.mutate({ key, value: next })}
        />
      )
    }

    // Asosiy kanal — ro'yxatdan. Erkin matn bo'lsa, xato yozilgan
    // qiymat ("telegramm") jimgina SMS'ga qaytarardi.
    if (key === 'notifications.default_channel') {
      return (
        <select
          value={String(value ?? 'telegram')}
          disabled={!editable}
          onChange={(event) => save.mutate({ key, value: event.target.value })}
          className="rounded-lg border border-tosh-200 px-2.5 py-1.5 text-sm outline-none focus:border-nihol-500 disabled:bg-tosh-50"
        >
          <option value="telegram">{t('Telegram')}</option>
          <option value="sms">{t('SMS')}</option>
        </select>
      )
    }

    if (key === 'general.default_language') {
      return (
        <select
          value={String(value ?? 'uz')}
          disabled={!editable}
          aria-label={META[key]?.label ?? key}
          onChange={(e) => save.mutate({ key, value: e.target.value })}
          className="w-44 rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50"
        >
          {APP_LOCALES.map((locale) => (
            <option key={locale.code} value={locale.code}>
              {locale.label}
            </option>
          ))}
        </select>
      )
    }

    if (typeof value === 'boolean') {
      return (
        <Switch
          checked={value}
          onChange={(next) => save.mutate({ key, value: next })}
          disabled={!editable || save.isPending}
          label={META[key]?.label ?? key}
        />
      )
    }

    if (typeof value === 'number') {
      return (
        <input
          type="number"
          min={1}
          max={31}
          defaultValue={value}
          disabled={!editable}
          aria-label={META[key]?.label ?? key}
          onBlur={(e) => {
            const next = Number(e.target.value)
            if (Number.isFinite(next) && next !== value) save.mutate({ key, value: next })
          }}
          className="w-24 rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50"
        />
      )
    }

    return (
      <input
        defaultValue={String(value ?? '')}
        disabled={!editable}
        aria-label={META[key]?.label ?? key}
        onBlur={(e) => {
          if (e.target.value !== String(value ?? '')) save.mutate({ key, value: e.target.value })
        }}
        className="w-56 rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50"
      />
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Sozlamalar')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Oʻzgarish darhol saqlanadi va tashkilotning barcha filiallariga tegishli.')}
        </p>
      </div>

      {/* "SMS yoqilgan" degan sozlama ko'rinib turgan joyda, SMS
          haqiqatda yuborilmayotgani ham ko'rinishi kerak (PLAN 3.2). */}
      <TestModeBanner />

      {!editable && (
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {t('Sozlamalarni faqat koʻrishingiz mumkin.')}
        </div>
      )}
      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {GROUPS.map(([prefix, title]) => {
        const groupKeys = keys.filter((key) => key.startsWith(`${prefix}.`))
        if (groupKeys.length === 0) return null
        // Shartnoma rekvizitlari faqat shartnomalar yoqilganda kerak
        // (PLAN 9.3): o'chirilgan bo'limning sozlamasi ekranni
        // sababsiz uzaytiradi.
        if (prefix === 'contracts' && !contractsOn) return null
        return (
          <section
            key={prefix}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white"
          >
            <h2 className="border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-900">
              {title}
            </h2>
            <div className="divide-y divide-slate-100">
              {groupKeys.map((key) => (
                <div key={key} className="flex items-center justify-between gap-4 px-4 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900">{META[key]?.label ?? key}</p>
                    <p className="text-xs text-slate-500">{META[key]?.help ?? key}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {savedKey === key && !save.isPending && (
                      <span className="text-xs text-emerald-600">{t('Saqlandi')}</span>
                    )}
                    {renderControl(key, settings[key])}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )
      })}

      <OnlinePaymentSettings />

      {contractsOn && <ContractTemplatesSettings />}
    </div>
  )
}
