/**
 * "Bizni qayerdan eshitishgan?" (Bosqich 14) — varonka koʻrinishida.
 *
 * Davrda qoʻshilgan bolalar oila bogʻcha haqida qayerdan eshitgani
 * boʻyicha. Eng koʻp bola keltirgan manba tepada va eng keng; pastga
 * qarab torayadi — har tasma oʻzidan keyingisining kengligiga qarab
 * qiyalanadi, shuning uchun shakl yaxlit varonka boʻlib koʻrinadi.
 * Ranglar brend ketma-ketligidan (`CHART_SEQUENCE`, koʻk/binafsha yoʻq):
 * yorugʻligi almashib turadi, yonma-yon tasmalar ajralib turadi.
 *
 * Rang yolgʻiz maʼno tashimaydi: har qatorda nomi, soni va ulushi matn
 * bilan yozilgan. Javob berilmaganlar varonkaga kirmaydi — ular manba
 * emas — pastda alohida qator.
 */

import { useQuery } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'framer-motion'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { reportsApi } from '@/features/dashboard/api'
import { CHART_SEQUENCE } from '@/lib/brand'
import { number } from '@/lib/format'
import { t } from '@/lib/i18n'

/** Eng kichik tasma ham koʻrinsin (foizda). */
const MIN_WIDTH = 10

export function SourcesReport({ from, to }: { from: string; to: string }) {
  const organizationId = useOrganizationId()
  const reduceMotion = useReducedMotion()
  const report = useQuery({
    queryKey: ['org', organizationId, 'reports', 'sources', from, to],
    queryFn: () => reportsApi.sources(from, to),
  })
  const data = report.data
  if (!data) return null

  const rows = [...data.rows].sort((a, b) => b.count - a.count)
  const top = Math.max(1, ...rows.map((row) => row.count))
  const widths = rows.map((row) => Math.max(MIN_WIDTH, (row.count / top) * 100))

  return (
    <section
      aria-labelledby="sources-title"
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 id="sources-title" className="text-sm font-semibold text-slate-900">
            {t('Bizni qayerdan eshitishgan?')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Davrda qoʻshilgan bolalar — oila bogʻcha haqida qayerdan bilgani boʻyicha.')}
          </p>
        </div>
        <p className="num text-lg font-bold text-slate-900">
          {t('{n} bola', { n: number(data.total) })}
        </p>
      </div>

      {data.total === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{t('Bu davrda yangi bola qoʻshilmagan.')}</p>
      ) : (
        <ol className="mt-4 space-y-1">
          {rows.map((row, index) => {
            const width = widths[index]
            // Pastki qirra — keyingi tasmaning kengligi; oxirgisi biroz torayadi.
            const next = index + 1 < widths.length ? widths[index + 1] : width * 0.7
            const topInset = (100 - width) / 2
            const bottomInset = (100 - next) / 2
            const color = CHART_SEQUENCE[index % CHART_SEQUENCE.length]
            return (
              <motion.li
                key={row.source}
                className="grid grid-cols-[minmax(0,8rem)_minmax(0,1fr)_auto] items-center gap-3 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_auto]"
                initial={reduceMotion ? false : { opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                // Pastdan tepaga: eng pastki tasma birinchi chiqadi.
                transition={{ duration: 0.35, delay: (rows.length - 1 - index) * 0.09 }}
              >
                <span className="truncate text-sm text-slate-800" title={row.label}>
                  {row.label}
                </span>
                <div
                  aria-hidden
                  className="h-10"
                  style={{
                    backgroundColor: color,
                    clipPath: `polygon(${topInset}% 0, ${100 - topInset}% 0, ${
                      100 - bottomInset
                    }% 100%, ${bottomInset}% 100%)`,
                  }}
                />
                <span className="text-right text-sm tabular-nums">
                  <span className="font-semibold text-slate-900">{number(row.count)}</span>
                  <span className="ml-1 text-xs text-slate-500">{row.share}%</span>
                  <span className="block text-xs text-slate-500">
                    {t('hozir {n}', { n: number(row.active) })}
                  </span>
                </span>
              </motion.li>
            )
          })}
        </ol>
      )}

      {data.unanswered > 0 && (
        <p className="mt-3 text-xs text-slate-500">
          {t('Koʻrsatilmagan: {n} bola ({share}%) — varonkaga kirmaydi.', {
            n: number(data.unanswered),
            share: ((data.unanswered * 100) / data.total).toFixed(1),
          })}
        </p>
      )}
    </section>
  )
}
