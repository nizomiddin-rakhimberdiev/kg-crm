/**
 * Kitchen tab of the Inventory page (PLAN 6.6).
 *
 * Two jobs: keep the recipes (per ONE portion, in the product's own unit)
 * and serve a day's menu. Serving shows its preview first — portions from
 * today's register plus staff, and exactly what leaves the store — the
 * same "see it before it happens" pattern as invoice generation. A
 * shortage blocks serving and names the product; the fix is a purchase or
 * an adjustment on the Store tab.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChefHat, Plus, Trash2, UtensilsCrossed, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { DateInput } from '@/components/ui/DateInput'
import { inventoryApi } from '@/features/inventory/api'
import { kitchenApi, type Dish, type Meal } from '@/features/kitchen/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { quantity, som, today as todayIso, unitLabel } from '@/lib/format'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const MEALS: Array<[Meal, string]> = [
  ['breakfast', t('Nonushta')],
  ['lunch', t('Tushlik')],
  ['snack', t('Poldnik')],
  ['dinner', t('Kechki ovqat')],
]
const MEAL_LABEL = Object.fromEntries(MEALS) as Record<Meal, string>

const field =
  'rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500'

export function KitchenPanel() {
  return (
    <div className="space-y-6">
      <MenuDaySection />
      <DishesSection />
    </div>
  )
}

// --- Dishes ---

type DishDraft = {
  id: string | null
  name: string
  portion_grams: string
  ingredients: Array<{ product_id: string; quantity: string }>
}

function DishesSection() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const editable = can('inventory.update')
  const key = ['org', organizationId, 'kitchen', 'dishes']

  const dishesQuery = useQuery({ queryKey: key, queryFn: kitchenApi.dishes })
  const productsQuery = useQuery({
    queryKey: queryKeys.products(organizationId),
    queryFn: () => inventoryApi.products(),
  })
  const products = productsQuery.data?.items ?? []

  const [draft, setDraft] = useState<DishDraft | null>(null)
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: (value: DishDraft) =>
      kitchenApi.saveDish(value.id, {
        name: value.name.trim(),
        portion_grams: value.portion_grams ? Number(value.portion_grams) : null,
        ingredients: value.ingredients.filter((row) => row.product_id && row.quantity),
      }),
    onSuccess: () => {
      setDraft(null)
      setError(null)
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.')),
  })
  const remove = useMutation({
    mutationFn: kitchenApi.removeDish,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: key }),
  })

  const edit = (dish: Dish) =>
    setDraft({
      id: dish.id,
      name: dish.name,
      portion_grams: dish.portion_grams ? String(dish.portion_grams) : '',
      ingredients: dish.ingredients.map((row) => ({
        product_id: row.product_id,
        quantity: row.quantity,
      })),
    })

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <ChefHat className="h-4 w-4 text-slate-500" />
          {t('Taomlar (bir porsiya uchun)')}
        </h2>
        {editable && !draft && (
          <button
            type="button"
            onClick={() =>
              setDraft({
                id: null,
                name: '',
                portion_grams: '',
                ingredients: [{ product_id: '', quantity: '' }],
              })
            }
            className="flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:underline"
          >
            <Plus className="h-4 w-4" />
            {t('Yangi taom')}
          </button>
        )}
      </div>

      <ul className="divide-y divide-slate-100">
        {(dishesQuery.data?.items ?? []).map((dish) => (
          <li key={dish.id} className="flex items-start gap-3 py-2">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-900">
                {dish.name}
                {dish.portion_grams && (
                  <span className="ml-1.5 text-xs font-normal text-slate-500">
                    {t('{g} g', { g: dish.portion_grams })}
                  </span>
                )}
              </p>
              <p className="text-xs text-slate-500">
                {dish.ingredients
                  .map((row) => `${row.product} ${quantity(row.quantity, row.unit)}`)
                  .join(' · ')}
              </p>
            </div>
            <span className="shrink-0 text-xs text-slate-500">
              {dish.cost_per_portion !== null
                ? t('Porsiya: {money}', { money: som(dish.cost_per_portion) })
                : t('Narx nomaʼlum')}
            </span>
            {editable && (
              <span className="flex shrink-0 gap-1">
                <button
                  type="button"
                  onClick={() => edit(dish)}
                  className="rounded px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100"
                >
                  {t('Tahrirlash')}
                </button>
                <button
                  type="button"
                  aria-label={t('Oʻchirish')}
                  title={t('Oʻchirish')}
                  onClick={() => remove.mutate(dish.id)}
                  className="rounded p-1 text-slate-500 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </span>
            )}
          </li>
        ))}
        {(dishesQuery.data?.items ?? []).length === 0 && !dishesQuery.isPending && (
          <li className="py-3 text-sm text-slate-500">{t('Taom hali yoʻq.')}</li>
        )}
      </ul>

      {draft && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate(draft)
          }}
          className="mt-3 space-y-3 rounded-xl bg-slate-50 p-3"
        >
          <div className="grid gap-3 sm:grid-cols-[1fr_8rem]">
            <div>
              <label htmlFor="dish-name" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Nomi')}
              </label>
              <input
                id="dish-name"
                required
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                className={cn(field, 'w-full')}
              />
            </div>
            <div>
              <label htmlFor="dish-grams" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Porsiya, g')}
              </label>
              <input
                id="dish-grams"
                inputMode="numeric"
                value={draft.portion_grams}
                onChange={(event) =>
                  setDraft({ ...draft, portion_grams: event.target.value.replace(/\D/g, '') })
                }
                className={cn(field, 'w-full')}
              />
            </div>
          </div>

          <p className="text-xs font-medium text-slate-600">
            {t('Masalliqlar — bir porsiyaga, mahsulot oʻlchovida')}
          </p>
          {draft.ingredients.map((row, index) => {
            const unit = products.find((product) => product.id === row.product_id)?.unit ?? ''
            const update = (patch: Partial<typeof row>) =>
              setDraft({
                ...draft,
                ingredients: draft.ingredients.map((r, i) =>
                  i === index ? { ...r, ...patch } : r,
                ),
              })
            return (
              <div key={index} className="flex items-center gap-2">
                <select
                  aria-label={t('Mahsulot')}
                  value={row.product_id}
                  onChange={(event) => update({ product_id: event.target.value })}
                  className={cn(field, 'min-w-0 flex-1')}
                >
                  <option value="">{t('Mahsulot')}</option>
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.name}
                    </option>
                  ))}
                </select>
                <input
                  aria-label={t('Miqdor')}
                  inputMode="decimal"
                  value={row.quantity}
                  onChange={(event) => update({ quantity: event.target.value.replace(',', '.') })}
                  className={cn(field, 'w-24 text-right')}
                />
                <span className="w-10 text-xs text-slate-500">{unitLabel(unit)}</span>
                <button
                  type="button"
                  aria-label={t('Oʻchirish')}
                  title={t('Oʻchirish')}
                  onClick={() =>
                    setDraft({
                      ...draft,
                      ingredients: draft.ingredients.filter((_, i) => i !== index),
                    })
                  }
                  className="rounded p-1 text-slate-500 hover:bg-red-50 hover:text-red-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
          <button
            type="button"
            onClick={() =>
              setDraft({
                ...draft,
                ingredients: [...draft.ingredients, { product_id: '', quantity: '' }],
              })
            }
            className="text-xs font-medium text-brand-600 hover:underline"
          >
            {t('+ masalliq')}
          </button>

          {error && (
            <p role="alert" className="text-sm text-red-700">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setDraft(null)
                setError(null)
              }}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={save.isPending}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
          </div>
        </form>
      )}
    </section>
  )
}

// --- A day's menu ---

function MenuDaySection() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [day, setDay] = useState(todayIso())
  const [staff, setStaff] = useState('0')
  const [items, setItems] = useState<Array<{ dish_id: string; meal: Meal }> | null>(null)
  const [warehouseId, setWarehouseId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const dayKey = ['org', organizationId, 'kitchen', 'menu', day]

  const menuQuery = useQuery({
    queryKey: dayKey,
    queryFn: () => kitchenApi.menuDays(day, day),
  })
  const menu = menuQuery.data?.items[0] ?? null
  const dishesQuery = useQuery({
    queryKey: ['org', organizationId, 'kitchen', 'dishes'],
    queryFn: kitchenApi.dishes,
  })
  const warehousesQuery = useQuery({
    queryKey: queryKeys.warehouses(organizationId),
    queryFn: inventoryApi.warehouses,
  })
  const staffCount = Number(staff) || 0
  const previewQuery = useQuery({
    queryKey: [...dayKey, 'preview', menu?.id, staffCount],
    queryFn: () => kitchenApi.preview(menu!.id, staffCount),
    enabled: Boolean(menu && menu.status === 'draft' && menu.items.length > 0),
  })

  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
  const refresh = () => {
    setError(null)
    void queryClient.invalidateQueries({ queryKey: dayKey })
    invalidateMoney(queryClient, organizationId)
  }

  const plan = useMutation({
    mutationFn: () =>
      kitchenApi.plan({
        menu_date: day,
        warehouse_id: warehouseId || menu?.warehouse || warehousesQuery.data?.items[0]?.id || '',
        items: (items ?? []).filter((row) => row.dish_id),
      }),
    onSuccess: () => {
      setItems(null)
      refresh()
    },
    onError: fail,
  })
  const serve = useMutation({
    mutationFn: () => kitchenApi.serve(menu!.id, staffCount),
    onSuccess: refresh,
    onError: fail,
  })
  const unserve = useMutation({
    mutationFn: () => kitchenApi.unserve(menu!.id),
    onSuccess: refresh,
    onError: fail,
  })

  const editing = items !== null
  const preview = previewQuery.data

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex flex-wrap items-end gap-3">
        <h2 className="flex flex-1 items-center gap-2 text-sm font-semibold text-slate-900">
          <UtensilsCrossed className="h-4 w-4 text-slate-500" />
          {t('Kunlik menyu')}
        </h2>
        <div>
          <label htmlFor="menu-day" className="mb-1 block text-xs text-slate-600">
            {t('Sana')}
          </label>
          <DateInput
            id="menu-day"
            value={day}
            onChange={(value) => {
              setDay(value)
              setItems(null)
            }}
          />
        </div>
      </div>

      {menu?.status === 'served' && (
        <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {t('Berildi: {children} bola + {staff} xodim porsiyasi.', {
            children: menu.children_portions ?? 0,
            staff: menu.staff_portions,
          })}
        </p>
      )}

      {!editing && (
        <ul className="space-y-1">
          {(menu?.items ?? []).map((item) => (
            <li key={`${item.meal}-${item.dish_id}`} className="flex gap-2 text-sm">
              <span className="w-28 text-slate-500">{MEAL_LABEL[item.meal]}</span>
              <span className="text-slate-900">{item.dish}</span>
            </li>
          ))}
          {(menu?.items ?? []).length === 0 && (
            <li className="text-sm text-slate-500">{t('Bu kunga menyu tuzilmagan.')}</li>
          )}
        </ul>
      )}

      {editing && (
        <div className="space-y-2 rounded-xl bg-slate-50 p-3">
          <div>
            <label htmlFor="menu-store" className="mb-1 block text-xs text-slate-600">
              {t('Qaysi ombordan')}
            </label>
            <select
              id="menu-store"
              value={warehouseId || menu?.warehouse || ''}
              onChange={(event) => setWarehouseId(event.target.value)}
              className={field}
            >
              {(warehousesQuery.data?.items ?? []).map((warehouse) => (
                <option key={warehouse.id} value={warehouse.id}>
                  {warehouse.name}
                </option>
              ))}
            </select>
          </div>
          {items.map((row, index) => (
            <div key={index} className="flex items-center gap-2">
              <select
                aria-label={t('Ovqatlanish')}
                value={row.meal}
                onChange={(event) =>
                  setItems(
                    items.map((r, i) =>
                      i === index ? { ...r, meal: event.target.value as Meal } : r,
                    ),
                  )
                }
                className={field}
              >
                {MEALS.map(([code, label]) => (
                  <option key={code} value={code}>
                    {label}
                  </option>
                ))}
              </select>
              <select
                aria-label={t('Taom')}
                value={row.dish_id}
                onChange={(event) =>
                  setItems(
                    items.map((r, i) => (i === index ? { ...r, dish_id: event.target.value } : r)),
                  )
                }
                className={cn(field, 'min-w-0 flex-1')}
              >
                <option value="">{t('Taom')}</option>
                {(dishesQuery.data?.items ?? []).map((dish) => (
                  <option key={dish.id} value={dish.id}>
                    {dish.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                aria-label={t('Oʻchirish')}
                title={t('Oʻchirish')}
                onClick={() => setItems(items.filter((_, i) => i !== index))}
                className="rounded p-1 text-slate-500 hover:bg-red-50 hover:text-red-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => setItems([...items, { dish_id: '', meal: 'lunch' }])}
              className="text-xs font-medium text-brand-600 hover:underline"
            >
              {t('+ taom')}
            </button>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setItems(null)}
                className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
              >
                {t('Bekor qilish')}
              </button>
              <button
                type="button"
                disabled={plan.isPending}
                onClick={() => plan.mutate()}
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {t('Menyuni saqlash')}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {can('inventory.create') && !editing && menu?.status !== 'served' && (
        <button
          type="button"
          onClick={() =>
            setItems(menu?.items.map(({ dish_id, meal }) => ({ dish_id, meal })) ?? [])
          }
          className="mt-3 text-sm font-medium text-brand-600 hover:underline"
        >
          {menu ? t('Menyuni oʻzgartirish') : t('Menyu tuzish')}
        </button>
      )}

      {/* Preview before serving — what leaves the store, product by product. */}
      {preview && !editing && menu?.status === 'draft' && (
        <div className="mt-4 space-y-3 border-t border-slate-100 pt-3">
          <div className="flex flex-wrap items-end gap-3">
            <p className="flex-1 text-sm text-slate-700">
              {t('Davomat boʻyicha {n} bola', { n: preview.children_portions })}
            </p>
            <div>
              <label htmlFor="staff-portions" className="mb-1 block text-xs text-slate-600">
                {t('Xodimlar porsiyasi')}
              </label>
              <input
                id="staff-portions"
                inputMode="numeric"
                value={staff}
                onChange={(event) => setStaff(event.target.value.replace(/\D/g, ''))}
                className={cn(field, 'w-20 text-right')}
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-sm">
              <thead className="text-left text-xs text-slate-500">
                <tr>
                  <th className="py-1">{t('Mahsulot')}</th>
                  <th className="py-1 text-right">{t('Kerak')}</th>
                  <th className="py-1 text-right">{t('Omborda')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {preview.lines.map((line) => (
                  <tr
                    key={line.product_id}
                    className={Number(line.short) > 0 ? 'text-red-700' : 'text-slate-700'}
                  >
                    <td className="py-1">{line.product}</td>
                    <td className="num py-1 text-right">{quantity(line.needed, line.unit)}</td>
                    <td className="num py-1 text-right">{quantity(line.available, line.unit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {preview.has_shortage && (
            <p className="text-sm text-red-700">
              {t('Omborda yetmaydi — avval «Ombor» bandida kirim yoki tuzatish kiriting.')}
            </p>
          )}
          {can('inventory.create') && (
            <button
              type="button"
              disabled={serve.isPending || preview.has_shortage || preview.portions === 0}
              onClick={() => serve.mutate()}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {t('Berildi — {n} porsiya ombordan chiqarilsin', { n: preview.portions })}
            </button>
          )}
        </div>
      )}

      {menu?.status === 'served' && can('inventory.update') && (
        <button
          type="button"
          disabled={unserve.isPending}
          onClick={() => {
            if (window.confirm(t('«Berildi» bekor qilinsinmi? Mahsulotlar omborga qaytariladi.')))
              unserve.mutate()
          }}
          className="mt-3 text-sm text-slate-500 hover:text-red-600"
        >
          {t('«Berildi»ni bekor qilish')}
        </button>
      )}
    </section>
  )
}
