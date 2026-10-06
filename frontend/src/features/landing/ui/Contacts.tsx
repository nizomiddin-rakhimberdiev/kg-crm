/**
 * Aloqa bloki — header (mobil menyu) va footer uchun (PLAN 5.7).
 *
 * Maʼlumot `config/contact.ts` va `config/env.ts` dan: raqam bir
 * joyda oʻzgaradi. Yuridik qator (nomi, STIR, manzili) faqat
 * toʻldirilgan qismlardan yigʻiladi — boʻsh boʻlsa umuman yoʻq.
 */

import { Mail, Phone, Send } from 'lucide-react'
import { CONTACT, formatPhone, telegramUrl } from '@/config/contact'
import { env } from '@/config/env'
import { copy, type Locale } from '../content'

/** Telefon(lar), Telegram, email — ustma-ust. */
export function ContactList({ locale, className = '' }: { locale: Locale; className?: string }) {
  const t = copy[locale].contact
  const row =
    'inline-flex min-h-[44px] items-center gap-2.5 py-1 text-[15px] text-slate-700 transition hover:text-slate-950'
  return (
    <ul className={`grid gap-2.5 ${className}`}>
      {CONTACT.phones.map((phone) => (
        <li key={phone}>
          <a href={`tel:${phone}`} className={`${row} tabular-nums`}>
            <Phone aria-hidden="true" className="h-4 w-4 text-brand-600" />
            {formatPhone(phone)}
          </a>
        </li>
      ))}
      <li>
        <a href={telegramUrl} target="_blank" rel="noopener noreferrer" className={row}>
          <Send aria-hidden="true" className="h-4 w-4 text-brand-600" />@{CONTACT.telegram}
          <span className="sr-only"> ({t.telegram})</span>
        </a>
      </li>
      <li>
        <a href={`mailto:${CONTACT.email}`} className={row}>
          <Mail aria-hidden="true" className="h-4 w-4 text-brand-600" />
          {CONTACT.email}
        </a>
      </li>
    </ul>
  )
}

/** "MChJ Nomi · STIR 123 · Manzil" — faqat toʻldirilgan qismlar. */
export function LegalLine({ locale, className = '' }: { locale: Locale; className?: string }) {
  const t = copy[locale].contact
  const parts = [
    env.legalEntityName,
    env.legalTin ? `${t.tin} ${env.legalTin}` : '',
    env.legalAddress,
  ].filter(Boolean)
  if (parts.length === 0) return null
  return <p className={`text-[13px] leading-5 text-slate-500 ${className}`}>{parts.join(' · ')}</p>
}

/** Header uchun ixcham: asosiy raqam (keng ekranda matn) + Telegram belgisi. */
export function HeaderContacts({ locale }: { locale: Locale }) {
  const t = copy[locale].contact
  const [phone] = CONTACT.phones
  const link =
    'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-[15px] font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 group-data-[dark]/nav:text-slate-300 group-data-[dark]/nav:hover:bg-white/10 group-data-[dark]/nav:hover:text-white'
  return (
    <div className="flex items-center">
      {phone && (
        <a
          href={`tel:${phone}`}
          className={`${link} tabular-nums`}
          aria-label={`${t.call}: ${formatPhone(phone)}`}
        >
          <Phone aria-hidden="true" className="h-4 w-4" />
          <span className="hidden xl:inline">{formatPhone(phone)}</span>
        </a>
      )}
      <a
        href={telegramUrl}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`${t.telegram}: @${CONTACT.telegram}`}
        className={link}
      >
        <Send aria-hidden="true" className="h-4 w-4" />
      </a>
    </div>
  )
}
