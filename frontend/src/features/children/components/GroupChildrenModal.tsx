/**
 * Guruh tarkibi — kim shu guruhda va nechta joy bo'sh (docs/04 §7.3).
 *
 * Ro'yxat ochiq a'zoliklardan hisoblanadi, `child.group` maydonidan emas:
 * bola guruhga vaqt bo'yicha biriktiriladi va o'tgan a'zoliklar tarixda
 * qoladi (docs/03 §11.5).
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Users2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { groupsApi } from '@/features/children/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { avatarTone, cn, initials } from '@/lib/utils'
import { t } from '@/lib/i18n'

export function GroupChildrenModal({
  groupId,
  groupName,
  onClose,
}: {
  groupId: string
  groupName: string
  onClose: () => void
}) {
  const organizationId = useOrganizationId()

  const query = useQuery({
    queryKey: queryKeys.groupChildren(organizationId, groupId),
    queryFn: () => groupsApi.children(groupId),
  })

  const data = query.data
  const limited = (data?.capacity ?? 0) > 0
  const full = limited && data?.free_seats === 0

  return (
    <Modal open onClose={onClose} className="max-w-lg">
      <div className="p-6">
        <div className="mb-4 flex items-center gap-3 pr-10">
          <div
            className={cn(
              'grid h-11 w-11 shrink-0 place-items-center rounded-xl text-sm font-bold',
              avatarTone(groupName),
            )}
          >
            {initials(groupName)}
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-lg font-bold text-slate-900">{groupName}</h2>
            <p className="text-sm text-slate-500">
              {data ? t('{length} ta bola', { length: data.children.length }) : t('Yuklanmoqda…')}
              {data && limited && ` / ${data.capacity}`}
            </p>
          </div>
        </div>

        {data && (
          <div
            className={cn(
              'mb-4 rounded-lg px-3 py-2 text-sm font-medium',
              !limited
                ? 'bg-slate-50 text-slate-600'
                : full
                  ? 'bg-amber-50 text-amber-800'
                  : 'bg-emerald-50 text-emerald-800',
            )}
          >
            {!limited
              ? t('Sigʻim cheklanmagan')
              : full
                ? t('Guruh toʻlgan — yangi bola qoʻshib boʻlmaydi')
                : t('{free_seats} ta joy boʻsh', { free_seats: data.free_seats })}
          </div>
        )}

        {query.isPending && (
          <p className="py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}
        {query.isError && (
          <p className="py-8 text-center text-sm text-red-600">
            {query.error instanceof ApiError
              ? query.error.message
              : t('Maʼlumotni yuklab boʻlmadi.')}
          </p>
        )}

        {data && data.children.length === 0 && (
          <div className="py-10 text-center">
            <Users2 className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">{t('Bu guruhda hozircha bola yoʻq.')}</p>
          </div>
        )}

        {data && data.children.length > 0 && (
          <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto scrollbar-thin">
            {data.children.map((child) => (
              <li key={child.id}>
                <Link
                  to={`/children/${child.id}`}
                  onClick={onClose}
                  className="group flex items-center gap-3 py-2.5 transition-colors hover:bg-slate-50"
                >
                  <span
                    className={cn(
                      'grid h-8 w-8 shrink-0 place-items-center rounded-full text-[11px] font-bold',
                      avatarTone(child.full_name),
                    )}
                  >
                    {initials(child.full_name)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-800 transition-colors group-hover:text-brand-700">
                      {child.last_name} {child.first_name}
                    </span>
                    <span className="block text-xs text-slate-400">
                      {t('{age_years} yosh', { age_years: child.age_years })}
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  )
}
