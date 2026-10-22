/**
 * Chiqim toifalarini ota-toifasi boʻyicha guruhlaydi (audit, 2026-10-21).
 *
 * Toifalar bazada ikki darajali ("Oziq-ovqat → Goʻsht"), lekin
 * tanlagichlarda yassi roʻyxat boʻlib chiqardi: yigirmatadan ortiq nom
 * tartibsiz, ota-toifasi koʻrinmaydi. `<optgroup>` bu ishni brauzerning
 * oʻzi qiladi — faqat roʻyxatni guruhlab berish kerak.
 *
 * Ota-toifasi yoʻqlari (Ijara, Transport…) OXIRIDA, sarlavhasiz
 * guruhda: ular oʻzi bir daraja, va ularga sunʼiy sarlavha
 * yasash roʻyxatni yana uzaytirardi.
 */

export interface GroupableCategory {
  id: string
  name: string
  parent_name?: string | null
}

export interface CategoryGroup<T extends GroupableCategory> {
  /** Ota-toifa nomi; bir darajali toifalar uchun boʻsh satr. */
  label: string
  items: T[]
}

export function groupCategories<T extends GroupableCategory>(
  categories: readonly T[],
): Array<CategoryGroup<T>> {
  const groups = new Map<string, T[]>()
  for (const category of categories) {
    const label = category.parent_name ?? ''
    const bucket = groups.get(label)
    if (bucket) bucket.push(category)
    else groups.set(label, [category])
  }
  const collator = new Intl.Collator('uz')
  return [...groups.entries()]
    .sort(([left], [right]) => {
      // Sarlavhasiz guruh — doimo oxirida.
      if (left === '') return 1
      if (right === '') return -1
      return collator.compare(left, right)
    })
    .map(([label, items]) => ({
      label,
      items: [...items].sort((left, right) => collator.compare(left.name, right.name)),
    }))
}
