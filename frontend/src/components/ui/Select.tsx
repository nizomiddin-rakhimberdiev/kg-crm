/**
 * Tanlagich — roʻyxat ham BIZNIKI (mijoz eʼtirozi, 2026-10-23).
 *
 * **Birinchi urinish nega yetmadi.** Avval native `<select>` qoldirilib,
 * faqat kiyimi almashtirilgan edi. Yopiq holati chiroyli chiqdi, lekin
 * OCHILGANDA brauzer oʻzining tizim roʻyxatini chizadi: macOS'da u
 * qora, maydon USTIGA tushadi va sahifaning qolganini yopib qoʻyadi.
 * Buni CSS bilan oʻzgartirib boʻlmaydi — tizim menyusi hujjatga
 * tegishli emas. Mijozning savoli oʻrinli edi: "pastdan dropdown
 * koʻrinishida chiroyli formada chiqishi kerak emasmidi?".
 *
 * **Nima saqlanib qoldi.** Roʻyxatni oʻzimiz chizish — native
 * elementdan keladigan hamma narsani qoʻlda qaytarish demak, va
 * ularning har biri shu yerda:
 *
 *  * klaviatura: ↑ ↓ Home End Enter Esc;
 *  * harf bilan qidirish ("g" bosib "Goʻsht" ga sakrash);
 *  * `optgroup` sarlavhalari va `disabled` variantlar;
 *  * skrinrider uchun `combobox` / `listbox` / `option` rollari;
 *  * **forma qiymati va `required` tekshiruvi** — koʻrinmaydigan,
 *    lekin FOKUSLANADIGAN native `<select>` orqali. Usiz "Bu
 *    maydonni toʻldiring" xabari ishlamay qolardi.
 *
 * **Nega roʻyxat portalda.** Modal va jadval `overflow` bilan
 * kesadi: absolyut joylashgan panel ularning ichida qirqilib
 * qolardi. Portal + `fixed` buni butunlay chetlab oʻtadi, oʻrni esa
 * tugmaning haqiqiy koordinatasidan hisoblanadi — joy yetmasa panel
 * tepaga ochiladi.
 *
 * Chaqiruvchilar uchun shartnoma OʻZGARMADI: ichida oʻsha
 * `<option>` va `<optgroup>` lar, `onChange` esa oʻsha
 * `event.target.value` ni beradi.
 */

import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type SelectHTMLAttributes,
} from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronDown, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  /**
   * `sm` — jadval qatori ichidagi zich tanlagich (36px).
   *
   * Sukut `md` — 40px: yonidagi matn maydonlari `px-3 py-2 text-sm`
   * bilan 38px, va 44px tanlagich ular ustidan oshib turardi.
   */
  size?: 'sm' | 'md'
  /** `dark` — platforma konsoli uchun (u qora fonda ishlaydi). */
  tone?: 'light' | 'dark'
  /** Maydon xato deb belgilangan — chekkasi qizgʻish boʻladi. */
  invalid?: boolean
  /** Chap tomondagi belgi — masalan filial tanlagichidagi bino. */
  icon?: LucideIcon
}

/** Roʻyxatdagi bitta qator: variant yoki guruh sarlavhasi. */
type Item =
  | { kind: 'option'; value: string; label: string; disabled: boolean }
  | { kind: 'group'; label: string }

/**
 * Roʻyxat NATIVE maydonning DOM'idan oʻqiladi, React bolalaridan emas.
 *
 * Avval bolalar oʻqilardi va u faqat toʻgʻridan-toʻgʻri yozilgan
 * `<option>` ni tanirdi. `<GroupOptions/>` kabi KOMPONENT esa oʻsha
 * paytda hali chizilmagan element — ichidagi variantlarni faqat React
 * chizgandan keyin bilish mumkin. Natijada mijozda guruh roʻyxati
 * boʻsh chiqdi (`/t/orientaltest`, 2026-10-28), yashirin maydonda esa
 * variantlar bor edi: forma ishladi, koʻz esa hech narsa koʻrmadi.
 *
 * DOM'dan oʻqish bu savolni butunlay yopadi: brauzer nimani variant
 * deb hisoblasa — biz ham oʻshani koʻrsatamiz, qaysi komponent uni
 * qaytarganidan qatʼi nazar.
 */
function readItems(element: HTMLSelectElement): Item[] {
  const out: Item[] = []
  const add = (option: HTMLOptionElement) =>
    out.push({
      kind: 'option',
      value: option.value,
      label: (option.textContent ?? '').trim(),
      disabled: option.disabled,
    })
  for (const node of Array.from(element.children)) {
    if (node instanceof HTMLOptGroupElement) {
      out.push({ kind: 'group', label: node.label })
      for (const child of Array.from(node.children)) {
        if (child instanceof HTMLOptionElement) add(child)
      }
      continue
    }
    if (node instanceof HTMLOptionElement) add(node)
  }
  return out
}

/** Ikki roʻyxat aynan birmi — qayta chizishni toʻxtatish uchun. */
function sameItems(a: Item[], b: Item[]): boolean {
  if (a.length !== b.length) return false
  return a.every((item, index) => {
    const other = b[index]
    if (item.kind !== other.kind) return false
    if (item.kind === 'group' || other.kind === 'group') return item.label === other.label
    return (
      item.value === other.value && item.label === other.label && item.disabled === other.disabled
    )
  })
}

/**
 * React'ning `onChange` i ishga tushishi uchun qiymat NATIVE yoʻl
 * bilan oʻrnatiladi: React element qiymatini kuzatib boradi va
 * oddiy `el.value = x` dan keyin oʻzgarishni "sezmaydi".
 */
function setNativeValue(element: HTMLSelectElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value')?.set
  setter?.call(element, value)
  element.dispatchEvent(new Event('change', { bubbles: true }))
}

export function Select({
  size = 'md',
  tone = 'light',
  invalid,
  icon: Icon,
  className,
  children,
  disabled,
  value,
  defaultValue,
  onChange,
  id,
  ...props
}: SelectProps) {
  const native = useRef<HTMLSelectElement>(null)
  const [items, setItems] = useState<Item[]>([])
  const options = items.filter(
    (item): item is Extract<Item, { kind: 'option' }> => item.kind === 'option',
  )

  const trigger = useRef<HTMLButtonElement>(null)
  const listId = useId()
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [rect, setRect] = useState<{ top: number; left: number; width: number } | null>(null)
  const search = useRef({ text: '', at: 0 })

  // Har chizishdan keyin roʻyxatni native maydondan qayta oʻqiymiz:
  // variantlar sorov natijasi bilan kelishi mumkin, va ular kelganda
  // React bizga xabar bermaydi — DOM esa allaqachon yangi.
  // `sameItems` toʻxtatgichi: holat faqat haqiqatan oʻzgarganda
  // yangilanadi, aks holda bu cheksiz qayta chizish boʻlardi.
  useLayoutEffect(() => {
    const element = native.current
    if (!element) return
    const next = readItems(element)
    setItems((previous) => (sameItems(previous, next) ? previous : next))
  })

  // Boshqarilmaydigan holat ham ishlashi kerak (`defaultValue`): o'shanda
  // haqiqat native maydonda, biz esa uni o'qiymiz.
  const [uncontrolled, setUncontrolled] = useState(() => String(defaultValue ?? ''))
  const current = value !== undefined ? String(value) : uncontrolled
  const selected = options.find((option) => option.value === current)

  const place = () => {
    const box = trigger.current?.getBoundingClientRect()
    if (!box) return
    // Joy yetmasa — tepaga. 288px = `max-h-72`.
    const below = window.innerHeight - box.bottom
    const height = Math.min(288, options.length * 40 + 8)
    const flip = below < height + 8 && box.top > below
    setRect({
      top: flip ? box.top - Math.min(height, box.top - 8) - 6 : box.bottom + 6,
      left: box.left,
      width: box.width,
    })
  }

  useLayoutEffect(() => {
    if (!open) return
    place()
    const onMove = () => place()
    window.addEventListener('scroll', onMove, true)
    window.addEventListener('resize', onMove)
    return () => {
      window.removeEventListener('scroll', onMove, true)
      window.removeEventListener('resize', onMove)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, options.length])

  // Faol variant roʻyxatdan chiqib ketmasin: uzun roʻyxatda (200 ta
  // bola) strelka bilan yurganda u koʻrinmay qolardi.
  useEffect(() => {
    if (!open) return
    const row = document.getElementById(listId)?.querySelector('[data-active="true"]')
    // `scrollIntoView` jsdom'da yoʻq — test muhitida jimgina oʻtkazib yuboriladi.
    if (row instanceof HTMLElement && typeof row.scrollIntoView === 'function') {
      row.scrollIntoView({ block: 'nearest' })
    }
    // `rect` ATAYLAB bogʻliqlikda: panel faqat oʻrni hisoblangandan
    // keyin chiziladi, ya'ni ochilish paytida u hali DOM'da yoʻq.
    // Usiz roʻyxat har safar tepadan ochilardi — oktabr tanlangan
    // boʻlsa ham "Yanvar" dan.
  }, [open, active, listId, rect])

  useEffect(() => {
    if (!open) return
    const outside = (event: MouseEvent) => {
      const target = event.target as Node
      if (trigger.current?.contains(target)) return
      if (document.getElementById(listId)?.contains(target)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', outside)
    return () => document.removeEventListener('mousedown', outside)
  }, [open, listId])

  const openList = () => {
    if (disabled) return
    const index = options.findIndex((option) => option.value === current)
    setActive(index < 0 ? 0 : index)
    setOpen(true)
  }

  const choose = (option: Extract<Item, { kind: 'option' }>) => {
    if (option.disabled) return
    setOpen(false)
    trigger.current?.focus()
    if (value === undefined) setUncontrolled(option.value)
    if (native.current) setNativeValue(native.current, option.value)
  }

  const step = (delta: number) => {
    if (!options.length) return
    let next = active
    for (let guard = 0; guard < options.length; guard += 1) {
      next = (next + delta + options.length) % options.length
      if (!options[next].disabled) break
    }
    setActive(next)
  }

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (disabled) return
    if (!open) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
        event.preventDefault()
        openList()
      }
      return
    }
    if (event.key === 'Escape' || event.key === 'Tab') {
      setOpen(false)
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      step(1)
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      step(-1)
      return
    }
    if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault()
      setActive(event.key === 'Home' ? 0 : options.length - 1)
      return
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      const option = options[active]
      if (option) choose(option)
      return
    }
    // Harf bilan qidirish — native elementdagidek: ketma-ket bosilgan
    // harflar bitta so'zga qo'shiladi, bir soniya jim turilsa — yangisi.
    if (event.key.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey) {
      const now = Date.now()
      search.current.text =
        now - search.current.at > 1000 ? event.key : search.current.text + event.key
      search.current.at = now
      const needle = search.current.text.toLocaleLowerCase()
      const hit = options.findIndex(
        (option) => !option.disabled && option.label.toLocaleLowerCase().startsWith(needle),
      )
      if (hit >= 0) setActive(hit)
    }
  }

  const field = cn(
    'flex w-full items-center justify-between gap-2 rounded-lg border bg-white pr-9 text-left outline-none transition-colors',
    Icon ? 'pl-9' : 'pl-3',
    size === 'sm' ? 'h-9 text-xs' : 'h-10 text-sm',
    tone === 'dark'
      ? 'border-slate-700 bg-slate-800 text-slate-100'
      : 'border-tosh-200 text-tosh-800',
    open && 'border-nihol-500 ring-2 ring-nihol-500/20',
    !open && 'focus-visible:border-nihol-500 focus-visible:ring-2 focus-visible:ring-nihol-500/20',
    invalid && 'border-orik-400',
    disabled && (tone === 'dark' ? 'opacity-50' : 'cursor-not-allowed bg-tosh-50 text-tosh-500'),
  )

  return (
    <div className={cn('relative w-full', className)}>
      {/*
        Haqiqiy maydon — forma uchun. Koʻrinmaydi, lekin FOKUSLANADI:
        `required` buzilganda brauzer aynan shu elementga fokus berib,
        xabarni uning ustida koʻrsatadi (`display:none` boʻlsa
        "focusable emas" deb xato beradi). Skrinrider uchun u yopiq —
        uning ishini tugma bajaradi.
      */}
      <select
        ref={native}
        tabIndex={-1}
        aria-hidden
        disabled={disabled}
        value={value}
        defaultValue={defaultValue}
        onChange={onChange}
        /*
          `id` bu yerda EMAS, tugmada: `<label for>` tugmani ko'rsatishi
          kerak (tugma ham `labelable` element). Ikkala elementga bir xil
          `id` berilsa, yorliq yashirilgan maydonni ko'rsatib qolardi va
          tanlagich nomsiz bo'lardi.
        */
        className="pointer-events-none absolute inset-0 h-full w-full opacity-0"
        {...props}
      >
        {children}
      </select>

      <button
        ref={trigger}
        type="button"
        role="combobox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-haspopup="listbox"
        aria-label={props['aria-label']}
        aria-labelledby={props['aria-labelledby']}
        aria-invalid={invalid || undefined}
        id={id}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={onKeyDown}
        className={field}
      >
        <span className={cn('truncate', !selected && 'text-tosh-500')}>
          {selected?.label ?? t('Tanlang')}
        </span>
      </button>

      {Icon && (
        <span
          className={cn(
            'pointer-events-none absolute inset-y-0 left-3 flex items-center',
            tone === 'dark' ? 'text-slate-400' : 'text-tosh-500',
            disabled && 'opacity-50',
          )}
        >
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      )}
      <span
        className={cn(
          'pointer-events-none absolute inset-y-0 right-3 flex items-center transition-transform',
          tone === 'dark' ? 'text-slate-400' : 'text-tosh-500',
          open && 'rotate-180',
          disabled && 'opacity-50',
        )}
      >
        <ChevronDown className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} aria-hidden />
      </span>

      {open &&
        rect &&
        createPortal(
          <ul
            id={listId}
            role="listbox"
            aria-label={props['aria-label']}
            style={{ top: rect.top, left: rect.left, minWidth: rect.width }}
            className={cn(
              'fixed z-[120] max-h-72 max-w-[min(26rem,calc(100vw-1.5rem))] overflow-y-auto overscroll-contain rounded-xl border py-1 shadow-xl',
              tone === 'dark' ? 'border-slate-700 bg-slate-800' : 'border-tosh-200 bg-white',
            )}
          >
            {items.map((item, index) =>
              item.kind === 'group' ? (
                <li
                  key={`g-${index}`}
                  role="group"
                  aria-label={item.label}
                  className={cn(
                    'px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide',
                    tone === 'dark' ? 'text-slate-400' : 'text-tosh-500',
                  )}
                >
                  {item.label}
                </li>
              ) : (
                <li key={`o-${item.value}-${index}`}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={item.value === current}
                    aria-disabled={item.disabled || undefined}
                    data-active={options[active] === item || undefined}
                    onMouseEnter={() => {
                      if (!item.disabled) setActive(options.indexOf(item))
                    }}
                    onClick={() => choose(item)}
                    className={cn(
                      'flex min-h-10 w-full items-center justify-between gap-3 px-3 text-left text-sm transition-colors',
                      item.disabled
                        ? tone === 'dark'
                          ? 'cursor-not-allowed text-slate-600'
                          : 'cursor-not-allowed text-tosh-300'
                        : options[active] === item
                          ? tone === 'dark'
                            ? 'bg-slate-700 text-white'
                            : 'bg-nihol-50 text-nihol-800'
                          : tone === 'dark'
                            ? 'text-slate-200'
                            : 'text-tosh-700',
                      item.value === current && !item.disabled && 'font-semibold',
                    )}
                  >
                    <span className="truncate">{item.label}</span>
                    {item.value === current && (
                      <Check className="h-4 w-4 shrink-0 text-nihol-600" aria-hidden />
                    )}
                  </button>
                </li>
              ),
            )}
          </ul>,
          document.body,
        )}
    </div>
  )
}
