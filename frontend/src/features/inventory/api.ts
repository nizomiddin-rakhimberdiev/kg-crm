import { api } from '@/lib/api/client'
import { withBranch } from '@/lib/branchScope'
import type { Product, ProductCategory, StockMovement, Supplier, Warehouse } from '@/lib/api/types'

export const inventoryApi = {
  products: (params?: Record<string, unknown>) => api.list<Product>('/products', params),
  createProduct: (payload: {
    name: string
    unit: string
    min_stock?: string
    category_id?: string | null
  }) => api.post<Product>('/products', withBranch(payload)),

  warehouses: () => api.list<Warehouse>('/warehouses'),
  createWarehouse: (payload: { name: string }) =>
    api.post<Warehouse>('/warehouses', withBranch(payload)),

  categories: () => api.list<ProductCategory>('/product-categories'),
  createCategory: (payload: { name: string }) =>
    api.post<ProductCategory>('/product-categories', withBranch(payload)),

  suppliers: () => api.list<Supplier>('/suppliers'),
  createSupplier: (payload: { name: string; phone?: string }) =>
    api.post<Supplier>('/suppliers', withBranch(payload)),

  movements: (params?: Record<string, unknown>) =>
    api.list<StockMovement>('/stock-movements', params),
  recordMovement: (payload: {
    product_id: string
    warehouse_id: string
    movement_type: string
    quantity: string
    direction?: string
    supplier_id?: string | null
    unit_cost?: string | null
    note?: string
  }) => api.post<StockMovement>('/stock-movements', payload),

  lowStock: () =>
    api.get<
      Array<{ id: string; name: string; unit: string; current_stock: string; min_stock: string }>
    >('/products/low-stock'),
}
