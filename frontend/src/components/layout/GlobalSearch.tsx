/**
 * Yuqoridagi qidiruv — ism, shartnoma raqami yoki ID bilan bola
 * topish (mijoz soʻrovi, 2026-10-28).
 *
 * **Nega yangidan yozildi.** Maydon har bir ekranda turardi va
 * "Ism yoki ID boʻyicha qidiruv..." deb vaʼda berardi, lekin unga
 * yozilgan narsa hech qayerga ketmasdi — na holat, na soʻrov, na
 * natija. Ishlamaydigan qidiruv yoʻq qidiruvdan yomonroq: odam uni
 * sinab koʻradi, natijasiz qoladi, va keyin tizimning qolgan
 * qismiga ham ishonmaydi.
 *
 * Qidiruv taʼrifi serverda bitta (`children/search.py`): ism,
 * shartnoma raqami yoki ID — bolalar roʻyxati, toʻlov doskasi va
 * qarzdorlar bilan AYNI.
 *
 * Roʻyxat portalda emas: maydon sarlavhada (`sticky`) turadi va
 * uning ostida hech narsa kesmaydi — `absolute` yetarli.
 */

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { childrenApi } from '@/features/children/api'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

/** Bitta harf butun roʻyxatni tortadi — ikkitadan boshlanadi. */
const MIN_LENGTH = 2
const DEBOUNCE_MS = 300

export function GlobalSearch({ className }: { className?: string }) {
  const { can } = useCan()
  const navigate = useNavigate()
  const organizationId = useOrganizationId()
  const [text, setText] = useState('')
  const [term, setTerm] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const box = useRef<HTMLDivElement>(null)

  // Har harfga soʻrov yubormaymiz: odam yozib boʻlguncha kutamiz.
  useEffect(() => {
    const trimmed = text.trim()
    if (trimmed.length < MIN_LENGTH) {
      setTerm('')
      return
    }
    const timer = setTimeout(() => setTerm(trimmed), DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [text])

  const found = useQuery({
    queryKey: ['org', organizationId, 'global-search', term],
    queryFn: () => childrenApi.list({ q: term, page_size: 8 }),
    enabled: term.length >= MIN_LENGTH,
  })

  const rows = term ? (found.data?.items ?? []) : []

  useEffect(() => {
    setActive(0)
  }, [term])

  // Tashqariga bosilganda yopiladi — roʻyxat sahifa ustida osilib
  // qolmasligi kerak.
  useEffect(() => {
    if (!open) return
    const outside = (event: MouseEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', outside)
    return () => document.removeEventListener('mousedown', outside)
  }, [open])

  if (!can('children.read')) return null

  const go = (id: string) => {
    setOpen(false)
    setText('')
    navigate(`/children/${id}`)
  }

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      setText('')
      setOpen(false)
      return
    }
    if (!rows.length) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActive((index) => (index + 1) % rows.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((index) => (index - 1 + rows.length) % rows.length)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      go(rows[active].id)
    }
  }

  return (
    <div ref={box} className={cn('relative', className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
      <input
        type="search"
        value={text}
        onChange={(event) => {
          setText(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={t('Ism, shartnoma raqami yoki ID…')}
        aria-label={t('Ism, shartnoma raqami yoki ID…')}
        // Brauzerning oʻz tozalash belgisi yashiriladi: bizniki
        // allaqachon bor va yonma-yon ikkita ✕ turardi.
        className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-9 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30 [&::-webkit-search-cancel-button]:hidden"
      />
      {text && (
        <button
          type="button"
          onClick={() => {
            setText('')
            setOpen(false)
          }}
          aria-label={t('Tozalash')}
          className="absolute right-2 top-1/2 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-md text-slate-400 transition hover:bg-slate-200 hover:text-slate-600"
        >
          <X className="h-4 w-4" />
        </button>
      )}

      {open && term.length >= MIN_LENGTH && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          {found.isPending ? (
            <p className="px-3 py-3 text-sm text-slate-500">{t('Qidirilmoqda…')}</p>
          ) : rows.length === 0 ? (
            <p className="px-3 py-3 text-sm text-slate-500">{t('Hech narsa topilmadi.')}</p>
          ) : (
            <ul role="listbox" className="max-h-80 overflow-y-auto py-1">
              {rows.map((row, index) => (
                <li key={row.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === active}
                    onMouseEnter={() => setActive(index)}
                    onClick={() => go(row.id)}
                    className={cn(
                      'flex w-full items-center justify-between gap-3 px-3 py-2 text-left',
                      index === active ? 'bg-slate-100' : 'hover:bg-slate-50',
                    )}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-slate-800">
                        {row.full_name}
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {[row.current_group?.name, row.contract_number]
                          .filter(Boolean)
                          .join(' · ') || t('guruhsiz')}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
