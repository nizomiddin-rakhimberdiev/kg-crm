/**
 * Ombor (docs/04 §12).
 *
 * Qoldiq to'g'ridan-to'g'ri tahrirlanmaydi — u harakatlardan hisoblanadi
 * (D3). Tuzatish kerak bo'lsa `adjustment` harakati yoziladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Package, Plus } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { inventoryApi } from '@/features/inventory/api'
import { KitchenPanel } from '@/features/kitchen/components/KitchenPanel'
import { useFeature } from '@/lib/features'
import { invalidateMoney } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Product } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { quantity, unitLabel } from '@/lib/format'
import { cn } from '@/lib/utils'
import { QueryError } from '@/components/ui/QueryError'
import { EmptyState } from '@/components/ui/EmptyState'
import { t } from '@/lib/i18n'

const UNITS = ['kg', 'g', 'l', 'ml', 'pcs', 'pack'] as const
const MOVEMENT_LABELS: Record<string, string> = {
  purchase: t('Xarid'),
  consumption: t('Isteʼmol'),
  adjustment: t('Tuzatish'),
  waste: t('Yaroqsiz'),
  transfer: t('Koʻchirish'),
}

export default function InventoryPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  // Store or kitchen (PLAN 6.6) — one page, one permission module.
  const [tab, setTab] = useState<'store' | 'kitchen'>('store')
  const kitchenOn = useFeature('kitchen')
  const [moving, setMoving] = useState<Product | null>(null)
  const [moveForm, setMoveForm] = useState({
    movement_type: 'purchase',
    quantity: '',
    unit_cost: '',
  })
  const [productForm, setProductForm] = useState({ name: '', unit: 'kg', min_stock: '' })
  const [error, setError] = useState<string | null>(null)

  const productsQuery = useQuery({
    queryKey: queryKeys.products(organizationId),
    queryFn: () => inventoryApi.products(),
  })
  const warehousesQuery = useQuery({
    queryKey: queryKeys.warehouses(organizationId),
    queryFn: inventoryApi.warehouses,
  })
  const movementsQuery = useQuery({
    queryKey: queryKeys.movements(organizationId, { product: moving?.id }),
    queryFn: () => inventoryApi.movements(moving ? { product: moving.id } : undefined),
    enabled: Boolean(moving),
  })

  const invalidate = () => {
    invalidateMoney(queryClient, organizationId)
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const createProduct = useMutation({
    mutationFn: () =>
      inventoryApi.createProduct({
        name: productForm.name,
        unit: productForm.unit,
        min_stock: productForm.min_stock || '0',
      }),
    onSuccess: () => {
      setProductForm({ name: '', unit: 'kg', min_stock: '' })
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const recordMovement = useMutation({
    mutationFn: () => {
      const warehouse = warehousesQuery.data?.items[0]
      if (!warehouse) throw new ApiError('VALIDATION_ERROR', t('Avval ombor yarating.'))
      return inventoryApi.recordMovement({
        product_id: moving!.id,
        warehouse_id: warehouse.id,
        movement_type: moveForm.movement_type,
        quantity: moveForm.quantity,
        unit_cost: moveForm.unit_cost || null,
      })
    },
    onSuccess: () => {
      setMoveForm({ movement_type: 'purchase', quantity: '', unit_cost: '' })
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const createWarehouse = useMutation({
    mutationFn: () => inventoryApi.createWarehouse({ name: 'Asosiy ombor' }),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const products = productsQuery.data?.items ?? []
  const lowCount = products.filter((p) => p.is_low_stock).length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Ombor')}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('Qoldiq harakatlardan hisoblanadi — toʻgʻridan-toʻgʻri tahrirlanmaydi.')}
          </p>
        </div>
        {lowCount > 0 && (
          <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            {t('{lowCount} ta mahsulot qoldigʻi past', { lowCount })}
          </div>
        )}
      </div>

      {kitchenOn && (
        <div role="tablist" className="flex gap-1 border-b border-slate-200">
          {(
            [
              ['store', t('Ombor')],
              ['kitchen', t('Oshxona')],
            ] as const
          ).map(([code, label]) => (
            <button
              key={code}
              type="button"
              role="tab"
              aria-selected={tab === code}
              onClick={() => setTab(code)}
              className={cn(
                '-mb-px border-b-2 px-3 py-2 text-sm font-medium transition',
                tab === code
                  ? 'border-brand-600 text-brand-700'
                  : 'border-transparent text-slate-500 hover:text-slate-800',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {kitchenOn && tab === 'kitchen' && <KitchenPanel />}

      {(tab === 'store' || !kitchenOn) && (
        <>
          {error && (
            <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {warehousesQuery.data?.items.length === 0 && can('inventory.create') && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
              <p className="text-slate-600">{t('Harakat yozish uchun avval ombor kerak.')}</p>
              <button
                type="button"
                onClick={() => createWarehouse.mutate()}
                className="mt-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                {t('Asosiy ombor yaratish')}
              </button>
            </div>
          )}

          {can('inventory.create') && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                createProduct.mutate()
              }}
              className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4"
            >
              <div className="min-w-[200px] flex-1">
                <label htmlFor="pname" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Mahsulot')}
                </label>
                <input
                  id="pname"
                  required
                  value={productForm.name}
                  onChange={(e) => setProductForm((p) => ({ ...p, name: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <div className="w-28">
                <label htmlFor="punit" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Birlik')}
                </label>
                <select
                  id="punit"
                  value={productForm.unit}
                  onChange={(e) => setProductForm((p) => ({ ...p, unit: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                >
                  {/* Kod bazada qoladi, ekranda esa nomi (audit, 2026-10-21). */}
                  {UNITS.map((u) => (
                    <option key={u} value={u}>
                      {unitLabel(u)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="w-32">
                <label htmlFor="pmin" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Min. qoldiq')}
                </label>
                <input
                  id="pmin"
                  type="number"
                  min={0}
                  step="0.001"
                  value={productForm.min_stock}
                  onChange={(e) => setProductForm((p) => ({ ...p, min_stock: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <button
                type="submit"
                disabled={createProduct.isPending}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                <Plus className="h-4 w-4" /> {t('Qoʻshish')}
              </button>
            </form>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setMoving(p)}
                className={cn(
                  'rounded-2xl border bg-white p-4 text-left transition hover:border-brand-300',
                  moving?.id === p.id ? 'border-brand-400' : 'border-slate-200',
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-900">{p.name}</p>
                    <p className="text-xs text-slate-500">{p.category_name ?? 'kategoriyasiz'}</p>
                  </div>
                  {p.is_low_stock && <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />}
                </div>
                <p
                  className={cn(
                    'mt-2 text-xl font-bold',
                    p.is_low_stock ? 'text-amber-700' : 'text-slate-900',
                  )}
                >
                  {quantity(p.current_stock, p.unit)}
                </p>
                {Number(p.min_stock) > 0 && (
                  <p className="text-xs text-slate-500">
                    {t('min {qty}', { qty: quantity(p.min_stock, p.unit) })}
                  </p>
                )}
              </button>
            ))}
          </div>

          {productsQuery.isError && (
            <QueryError
              error={productsQuery.error}
              onRetry={() => productsQuery.refetch()}
              className="rounded-2xl border border-slate-200 bg-white"
            />
          )}

          {products.length === 0 && !productsQuery.isPending && (
            <div className="rounded-2xl border border-slate-200 bg-white">
              {/* Boʻsh ekran KEYINGI QADAMNI aytadi (PLAN 4.7): "hozircha
              yoʻq" degan yozuvning oʻzi foydalanuvchini nima
              qilishini bilmagan holda qoldiradi. */}
              <EmptyState
                icon={Package}
                title={t('Hozircha mahsulot yoʻq')}
                hint={t(
                  'Oziq-ovqat, kanselyariya, tozalik — nima hisobga olinsa, shu yerda turadi.',
                )}
                action={
                  can('inventory.create') ? (
                    <button
                      type="button"
                      onClick={() => document.getElementById('pname')?.focus()}
                      className="rounded-lg bg-nihol-600 px-4 py-2 text-sm font-semibold text-white hover:bg-nihol-700"
                    >
                      {t('Mahsulot qoʻshish')}
                    </button>
                  ) : undefined
                }
              />
            </div>
          )}

          {moving && (
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-900">
                {t('{name} — harakatlar', { name: moving.name })}
              </h2>

              {can('inventory.create') && warehousesQuery.data?.items.length ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    recordMovement.mutate()
                  }}
                  className="mb-4 flex flex-wrap items-end gap-3 border-b border-slate-100 pb-4"
                >
                  <div className="w-40">
                    <label
                      htmlFor="mtype"
                      className="mb-1 block text-xs font-medium text-slate-600"
                    >
                      {t('Turi')}
                    </label>
                    <select
                      id="mtype"
                      value={moveForm.movement_type}
                      onChange={(e) =>
                        setMoveForm((p) => ({ ...p, movement_type: e.target.value }))
                      }
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                    >
                      {(['purchase', 'consumption', 'waste'] as const).map((t) => (
                        <option key={t} value={t}>
                          {MOVEMENT_LABELS[t]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="w-32">
                    <label htmlFor="mqty" className="mb-1 block text-xs font-medium text-slate-600">
                      {t('Miqdor')}
                    </label>
                    <input
                      id="mqty"
                      type="number"
                      required
                      min="0.001"
                      step="0.001"
                      value={moveForm.quantity}
                      onChange={(e) => setMoveForm((p) => ({ ...p, quantity: e.target.value }))}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                    />
                  </div>
                  {moveForm.movement_type === 'purchase' && (
                    <div className="w-36">
                      <label
                        htmlFor="mcost"
                        className="mb-1 block text-xs font-medium text-slate-600"
                      >
                        {t('Birlik narxi')}
                      </label>
                      <input
                        id="mcost"
                        type="number"
                        min={0}
                        step="0.01"
                        value={moveForm.unit_cost}
                        onChange={(e) => setMoveForm((p) => ({ ...p, unit_cost: e.target.value }))}
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                      />
                    </div>
                  )}
                  <button
                    type="submit"
                    disabled={recordMovement.isPending}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
                  >
                    {t('Yozish')}
                  </button>
                </form>
              ) : null}

              <ul className="divide-y divide-slate-100 text-sm">
                {movementsQuery.data?.items.map((m) => (
                  <li key={m.id} className="flex items-center justify-between py-2">
                    <span className="flex items-center gap-2 text-slate-700">
                      {m.direction === 'in' ? (
                        <ArrowDownRight className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <ArrowUpRight className="h-4 w-4 text-red-600" />
                      )}
                      {MOVEMENT_LABELS[m.movement_type] ?? m.movement_type}
                      {m.supplier_name && (
                        <span className="text-xs text-slate-500">· {m.supplier_name}</span>
                      )}
                    </span>
                    <span
                      className={cn(
                        'font-medium',
                        m.direction === 'in' ? 'text-emerald-700' : 'text-red-700',
                      )}
                    >
                      {m.direction === 'in' ? '+' : '−'}
                      {quantity(m.quantity, moving.unit)}
                    </span>
                  </li>
                ))}
                {movementsQuery.data?.items.length === 0 && (
                  <li className="py-4 text-center text-slate-500">{t('Harakat yoʻq.')}</li>
                )}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
