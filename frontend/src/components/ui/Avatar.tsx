/**
 * Avatar — rasm bo'lsa rasm, bo'lmasa bosh harflar.
 *
 * Bitta joyda: rasm yuklanmasa yoki o'chirilgan bo'lsa, ilova bo'ylab bir
 * xil zaxira ko'rinish ishlaydi. Media fayllar API bilan bir xil domenda
 * emas (Vite 5173, backend 8000), shuning uchun nisbiy `/media/...` yo'li
 * backend manziliga ulanadi.
 */

import { useState } from 'react'
import { env } from '@/config/env'
import { avatarTone, cn, initials } from '@/lib/utils'

/** `/media/...` → `http://127.0.0.1:8000/media/...` */
export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `${env.apiBaseUrl.replace(/\/api\/v1\/?$/, '')}${path}`
}

interface AvatarProps {
  name: string
  photoUrl?: string | null
  className?: string
  /** Bosh harflar o'lchami — konteyner o'lchamiga qarab beriladi. */
  textClassName?: string
}

export function Avatar({ name, photoUrl, className, textClassName }: AvatarProps) {
  const [failed, setFailed] = useState(false)
  const src = failed ? null : mediaUrl(photoUrl)

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        onError={() => setFailed(true)}
        className={cn('shrink-0 rounded-full object-cover', className)}
      />
    )
  }

  return (
    <span
      className={cn(
        'grid shrink-0 place-items-center rounded-full font-bold',
        avatarTone(name),
        className,
        textClassName,
      )}
    >
      {initials(name)}
    </span>
  )
}
