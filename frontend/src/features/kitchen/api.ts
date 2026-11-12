/** Kitchen — dishes, daily menu, serving from the store (PLAN 6.6). */

import { api } from '@/lib/api/client'
import { withBranch } from '@/lib/branchScope'

export type Meal = 'breakfast' | 'lunch' | 'snack' | 'dinner'

export interface Dish {
  id: string
  name: string
  portion_grams: number | null
  note: string
  ingredients: Array<{ product_id: string; product: string; unit: string; quantity: string }>
  /** At the latest purchase prices; `null` when a price is unknown. */
  cost_per_portion: string | null
}

export interface MenuDay {
  id: string
  menu_date: string
  warehouse: string
  warehouse_name: string
  status: 'draft' | 'served'
  children_portions: number | null
  staff_portions: number
  served_at: string | null
  items: Array<{ dish_id: string; dish: string; meal: Meal }>
}

export interface ServingPreview {
  children_portions: number
  staff_portions: number
  portions: number
  lines: Array<{
    product_id: string
    product: string
    unit: string
    needed: string
    available: string
    short: string
  }>
  has_shortage: boolean
}

export const kitchenApi = {
  dishes: () => api.listAll<Dish>('/dishes'),
  saveDish: (
    id: string | null,
    body: {
      name: string
      portion_grams: number | null
      ingredients: Array<{ product_id: string; quantity: string }>
    },
  ) =>
    id
      ? api.request<Dish>('put', `/dishes/${id}`, body)
      : api.post<Dish>('/dishes', withBranch(body)),
  removeDish: (id: string) => api.delete(`/dishes/${id}`),

  menuDays: (from: string, to: string) => api.list<MenuDay>('/menu-days', { from, to }),
  plan: (body: {
    menu_date: string
    warehouse_id: string
    items: Array<{ dish_id: string; meal: Meal }>
  }) => api.post<MenuDay>('/menu-days/plan', withBranch(body)),
  preview: (id: string, staffPortions: number) =>
    api.get<ServingPreview>(`/menu-days/${id}/preview`, { staff_portions: staffPortions }),
  serve: (id: string, staffPortions: number) =>
    api.post<MenuDay>(`/menu-days/${id}/serve`, { staff_portions: staffPortions }),
  unserve: (id: string) => api.post<MenuDay>(`/menu-days/${id}/unserve`, {}),
}
