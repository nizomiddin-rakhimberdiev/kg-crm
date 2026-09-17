/**
 * Brend belgisi — ildiz motividan olingan vaqtinchalik mark.
 *
 * Haqiqiy logotip tayyor bo'lgach, faqat shu fayldagi `<svg>` almashadi:
 * header, footer, legal sahifalar va hero — hammasi shu komponentni
 * ishlatadi, ya'ni brend bitta joydan boshqariladi.
 */

export function BrandMark({ className = 'h-9 w-9' }: { className?: string }) {
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-xl bg-slate-950 text-white ${className}`}
    >
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        {/* Poya va kurtak */}
        <path d="M12 20V9" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
        <path
          d="M12 12c0-2.4 1.9-4 4.2-4 0 2.4-1.9 4-4.2 4Z"
          fill="currentColor"
        />
        {/* Ildizlar */}
        <path
          d="M12 20c-2.6 0-4-1.3-5.2-3M12 20c2.6 0 4-1.3 5.2-3"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity=".65"
        />
      </svg>
    </span>
  )
}

export function Brand({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-2.5 font-bold tracking-[-0.02em] text-slate-950 ${className}`}
    >
      <BrandMark />
      <span>Radix CRM</span>
    </span>
  )
}
