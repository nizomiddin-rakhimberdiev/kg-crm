/**
 * "Nimadan boshlayman?" — boʻsh bogʻcha uchun zanjir (audit, 2026-10-21).
 *
 * Boʻsh akkauntda boshqaruv paneli nollar koʻrsatadi, va bu sotuvdan
 * keyingi birinchi taassurot. Bu karta nollar OʻRNIGA emas, ularning
 * USTIDA turadi: raqamlar oʻz joyida qoladi, lekin ekran avval nima
 * qilish kerakligini aytadi.
 *
 * Karta zanjir tugagach **oʻzi yoʻqoladi** — ishga tushgan bogʻchada u
 * shovqin. Shuning uchun uchinchi qadamning holati faqat kerak boʻlsa
 * soʻraladi: tarif va bola bor boʻlsa, qolgani bitta soʻrov.
 */

import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Check } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { nextStep, STEPS } from '@/features/dashboard/gettingStarted'
import { paymentsApi, tariffsApi } from '@/features/payments/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

/**
 * Zanjir tugaganini brauzerda eslab qolamiz.
 *
 * Aks holda ishga tushgan bogʻcha HAR safar dashboard ochganda ikkita
 * qoʻshimcha soʻrov yuborardi — faqat koʻrinmaydigan kartani
 * hisoblash uchun. Yozuv yoʻqolsa (boshqa brauzer, tozalangan
 * saqlash) eng yomoni — bir marta ortiqcha soʻrov.
 */
const doneKey = (organizationId: string) => `radix-started-${organizationId}`

function rememberedDone(organizationId: string): boolean {
  try {
    return localStorage.getItem(doneKey(organizationId)) === '1'
  } catch {
    return false
  }
}

export function GettingStarted({ activeChildren }: { activeChildren: number | undefined }) {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  // Zanjirni faqat uni BAJARA oladigan odam koʻradi: tarbiyachiga
  // "tarif yarating" degan maslahat bajarib boʻlmaydigan ish.
  const allowed =
    can('payments.create') && can('children.create') && !rememberedDone(organizationId)

  const tariffs = useQuery({
    queryKey: queryKeys.tariffs(organizationId),
    queryFn: tariffsApi.list,
    enabled: allowed,
    staleTime: 300_000,
  })

  const hasTariff = (tariffs.data?.items.length ?? 0) > 0
  const hasChildren = (activeChildren ?? 0) > 0
  const now = new Date()

  const summary = useQuery({
    queryKey: queryKeys.payments(organizationId, {
      boardSummary: `${now.getFullYear()}-${now.getMonth() + 1}`,
    }),
    queryFn: () => paymentsApi.boardSummary(now.getFullYear(), now.getMonth() + 1),
    // Uchinchi qadam faqat ikkinchisi bajarilgandan keyin maʼnoga ega.
    enabled: allowed && hasTariff && hasChildren,
    staleTime: 300_000,
  })

  if (!allowed || tariffs.isPending) return null
  // Uchinchi qadam javobi kelmaguncha zanjir koʻrsatilmaydi: "faktura
  // chiqaring" degan maslahat allaqachon chiqarilgan bogʻchada yolgʻon.
  if (hasTariff && hasChildren && summary.isPending) return null

  const hasInvoice = (summary.data?.with_invoice ?? 0) > 0
  const step = nextStep({ hasTariff, hasChildren, hasInvoice })
  if (step === null) {
    try {
      localStorage.setItem(doneKey(organizationId), '1')
    } catch {
      // Shaxsiy oyna yoki bloklangan saqlash — karta baribir
      // koʻrinmaydi, faqat keyingi safar yana hisoblanadi.
    }
    return null
  }

  const done: Record<string, boolean> = {
    tariff: hasTariff,
    child: hasChildren,
    invoice: hasInvoice,
  }

  return (
    <section
      aria-labelledby="getting-started-title"
      className="rounded-2xl border border-brand-200 bg-brand-50/40 p-4 sm:p-5"
    >
      <h2 id="getting-started-title" className="text-sm font-semibold text-slate-900">
        {t('Uch qadamda ishga tushadi')}
      </h2>
      <p className="mt-0.5 text-xs text-slate-600">
        {t('Tartib muhim: tarifsiz bolaga hisob-faktura chiqmaydi.')}
      </p>

      <ol className="mt-3 grid gap-2 sm:grid-cols-3">
        {STEPS.map((item, index) => {
          const complete = done[item.key]
          const current = item.key === step
          return (
            <li
              key={item.key}
              className={cn(
                'rounded-xl border bg-white p-3',
                current ? 'border-brand-400 ring-1 ring-brand-300' : 'border-slate-200',
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold',
                    complete ? 'bg-nihol-100 text-nihol-700' : 'bg-slate-100 text-slate-600',
                  )}
                >
                  {complete ? <Check className="h-3.5 w-3.5" aria-hidden /> : index + 1}
                </span>
                <span
                  className={cn(
                    'text-sm font-medium',
                    complete ? 'text-slate-500 line-through' : 'text-slate-900',
                  )}
                >
                  {item.title}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">{item.hint}</p>
              {current && (
                <Link
                  to={item.to}
                  className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-nihol-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-nihol-700"
                >
                  {t('Boshlash')}
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
