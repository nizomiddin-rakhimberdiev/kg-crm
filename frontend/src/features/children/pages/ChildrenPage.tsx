/**
 * Bolalar — tizimning markaziy ro'yxati (docs/04 §7).
 *
 * Filtr va qidiruv backend'da bajariladi: 300 bolali bog'chada butun
 * ro'yxatni brauzerga yuklab, u yerda filtrlash sahifani sekinlashtiradi
 * va sahifalash bilan ziddiyatga kiradi.
 *
 * Sahifalash ham serverda (docs/04 §3): `page`/`page_size` so'rovga
 * ketadi, `meta.pagination` javobdan o'qiladi. Filtr o'zgarganda sahifa
 * 1 ga qaytadi — aks holda "3-sahifa" yangi filtrda bo'sh chiqib,
 * "bola yo'q" degan noto'g'ri xulosa berardi.
 */

import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Phone, Plus, Search, Trash2, Upload, Users } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { clearDraft, draftKey, readDraft, writeDraft } from '@/lib/drafts'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { DateInput } from '@/components/ui/DateInput'
import { HEARD_FROM } from '@/features/children/heardFrom'
import { Pagination } from '@/components/ui/primitives'
import { childrenApi, groupsApi, type ChildInput } from '@/features/children/api'
import { ImportWizard } from '@/features/children/components/ImportWizard'
import { PricePicker } from '@/features/children/components/PricePicker'
import { priceFromChild, priceToPayload, type PriceValue } from '@/features/children/price'
import { tariffsApi } from '@/features/payments/api'
import { ageOutsideGroup } from '@/features/children/ageFit'
import { findDuplicate } from '@/features/children/duplicates'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { usePageState } from '@/hooks/usePageState'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Child } from '@/lib/api/types'
import { useToast } from '@/app/providers/ToastProvider'
import { documentProblem } from '@/features/children/documents'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { GroupOptions } from '@/features/children/components/GroupOptions'
import { useCan } from '@/lib/rbac/useCan'
import { formatDate, today } from '@/lib/format'
import { avatarTone, cn, initials } from '@/lib/utils'
import { t } from '@/lib/i18n'
import { FieldLabel } from '@/components/ui/FieldLabel'
import { Select } from '@/components/ui/Select'
import { STATUS_LABELS, STATUS_ORDER } from '@/features/children/status'

interface GuardianDraft {
  last_name: string
  first_name: string
  phone: string
  /** Ixtiyoriy ikkinchi raqam — bo'sh input formada turmaydi (PLAN 7.4). */
  phone_alt: string
  relation: string
}

const EMPTY_GUARDIAN_DRAFT: GuardianDraft = {
  last_name: '',
  first_name: '',
  phone: '',
  phone_alt: '',
  relation: 'mother',
}

/** Saqlanmagan "Yangi bola" formasi — sessionStorage'da (lib/drafts.ts). */
interface ChildDraft {
  form: ChildInput
  price: PriceValue
  formGroupId: string
  guardian: GuardianDraft
  showGuardianAlt: boolean
}

const EMPTY_FORM: ChildInput = {
  first_name: '',
  last_name: '',
  middle_name: '',
  date_of_birth: '',
  gender: 'male',
  // Qabul sanasi — sukut bo'yicha BUGUN.
  //
  // Bu maydon formada yo'q edi, va natijasi pulda ko'rindi: `enrolled_on`
  // bo'sh qolgani uchun birinchi oy proporsional hisoblanmasdi va oyning
  // 25-kunida kelgan bolaga ham to'liq oy yozilardi (productionda 21
  // boladan 21 tasi shunday edi). Sana BO'SH QOLDIRILMAYDI.
  enrolled_on: today(),
  // Qogʻozdagi shartnoma raqami (PLAN 9.3) — ixtiyoriy.
  contract_number: '',
  // Formada sukut — YANGI mijoz: qo'lda bola qo'shilayotganda u odatda
  // endi keladi. Import esa teskarisi (sukut "mavjud"), chunki u
  // tizimga o'tish quroli (PLAN 7.8).
  is_existing_client: false,
  skip_trial: false,
  opening_debt: '',
  // Bosqich 14: yangi bola qoʻshilganda tanlanmaguncha forma yuborilmaydi.
  heard_from: '',
  heard_from_note: '',
}

export default function ChildrenPage() {
  const organizationId = useOrganizationId()
  const { selectedBranchId } = useBranchScope()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const navigate = useNavigate()

  const [search, setSearch] = useState('')
  // Guruhni ro'yxatdan o'zgartirish TASDIQ bilan (PLAN 1.4): ilgari
  // sichqoncha g'ildiragining bitta aylanishi bolani boshqa guruhga
  // ko'chirib yuborardi va bu hech qayerda so'ralmasdi.
  const [pendingGroup, setPendingGroup] = useState<{ child: Child; groupId: string } | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim())
  const [statusFilter, setStatusFilter] = useState('')
  const [pageSize, setPageSize] = useState(25)
  const [showImport, setShowImport] = useState(false)
  // Saqlanmagan "Yangi bola" qoralamasi (2026-10-14): boshqa bo'limga
  // o'tib qaytilganda forma tozalanmaydi. Faqat YARATISH — tahrirlash
  // har safar serverdan yangi yuklanadi. `lib/drafts.ts` dagi izoh:
  // sessionStorage, chiqishda tozalanadi.
  const { user } = useAuth()
  const childDraftKey = draftKey(user?.id, 'children-create')
  const [restored] = useState(() => readDraft<ChildDraft>(childDraftKey))
  const [showForm, setShowForm] = useState(Boolean(restored))
  // `null` — yangi bola qo'shilyapti; obyekt — mavjudi tahrirlanyapti.
  const [editing, setEditing] = useState<Child | null>(null)
  const [form, setForm] = useState<ChildInput>(restored?.form ?? EMPTY_FORM)
  // Guruh bolaning MAYDONI emas — u alohida biriktirish (`/children/{id}/enroll`),
  // chunki bola guruhdan guruhga ko'chadi va har ko'chish tarixda qoladi.
  // Shuning uchun u formada alohida holat sifatida yuriladi.
  const [formGroupId, setFormGroupId] = useState(restored?.formGroupId ?? '')
  // Yaratish formasidagi IXTIYORIY vasiy bloki (PLAN 2.3). Ilgari
  // vasiyni ikkinchi ekranda qo'shish kerak edi va ko'pincha
  // unutilardi — vasiysiz bola esa SMS olmaydigan bola.
  const [guardian, setGuardian] = useState<GuardianDraft>(
    restored?.guardian ?? EMPTY_GUARDIAN_DRAFT,
  )
  const [showGuardianAlt, setShowGuardianAlt] = useState(restored?.showGuardianAlt ?? false)
  // Fayl qoralamaga yozilmaydi — brauzer uni saqlab bera olmaydi.
  const [contractFile, setContractFile] = useState<File | null>(null)
  const { toast } = useToast()
  // Narx — tarif yoki individual summa (PricePicker).
  const [price, setPrice] = useState<PriceValue>(
    restored?.price ?? { tariffId: null, monthlyFee: null },
  )
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  // Qoralama faqat nimadir yozilganda saqlanadi — bo'sh ochilgan forma
  // qaytib kelganda o'zi ochilib turmasin.
  useEffect(() => {
    if (!showForm || editing) return
    const draft: ChildDraft = { form, price, formGroupId, guardian, showGuardianAlt }
    const blank =
      JSON.stringify(form) === JSON.stringify(EMPTY_FORM) &&
      JSON.stringify(guardian) === JSON.stringify(EMPTY_GUARDIAN_DRAFT) &&
      !formGroupId &&
      !price.tariffId &&
      !price.monthlyFee
    if (blank) clearDraft(childDraftKey)
    else writeDraft(childDraftKey, draft)
  }, [showForm, editing, form, price, formGroupId, guardian, showGuardianAlt, childDraftKey])

  const closeForm = () => {
    clearDraft(childDraftKey)
    setShowForm(false)
    setEditing(null)
    setForm(EMPTY_FORM)
    setPrice({ tariffId: null, monthlyFee: null })
    setFormGroupId('')
    setGuardian(EMPTY_GUARDIAN_DRAFT)
    setShowGuardianAlt(false)
    setContractFile(null)
    setFieldErrors({})
    setError(null)
  }

  const openCreate = () => {
    if (showForm && !editing) return closeForm()
    setEditing(null)
    setForm(EMPTY_FORM)
    setPrice({ tariffId: null, monthlyFee: null })
    setFormGroupId('')
    setGuardian(EMPTY_GUARDIAN_DRAFT)
    setShowGuardianAlt(false)
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  const openEdit = (child: Child) => {
    setEditing(child)
    setForm({
      first_name: child.first_name,
      last_name: child.last_name,
      middle_name: child.middle_name ?? '',
      date_of_birth: child.date_of_birth,
      gender: child.gender,
      // Mavjud sana saqlanadi. Bo'sh bo'lsa bo'sh qoladi va MAJBURIY
      // emas: eski bolaga bugungi sanani jimgina yozib qo'yish uning
      // birinchi oyini noto'g'ri proporsional qilardi — eskilarni
      // `backfill_enrollment_dates` buyrug'i hal qiladi.
      enrolled_on: child.enrolled_on ?? '',
      contract_number: child.contract_number ?? '',
      heard_from: child.heard_from ?? '',
      heard_from_note: child.heard_from_note ?? '',
    })
    setPrice(priceFromChild(child))
    setFormGroupId(child.current_group?.id ?? '')
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  // Filtr yoki sahifa hajmi o'zgarsa — birinchi sahifadan (hosila, effekt emas).
  const [page, setPage] = usePageState(
    JSON.stringify([debouncedSearch, statusFilter, selectedBranchId, pageSize]),
  )

  const params = {
    page,
    page_size: pageSize,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(statusFilter ? { enrollment_status: statusFilter } : {}),
    ...(selectedBranchId ? { branch: selectedBranchId } : {}),
  }

  const childrenQuery = useQuery({
    queryKey: queryKeys.children(organizationId, params),
    queryFn: () => childrenApi.list(params),
    // Sahifa almashganda eski qatorlar yangisi kelguncha turadi —
    // jadval har bosishda bo'shab-to'lib "lipillamaydi".
    placeholderData: keepPreviousData,
  })

  // Bir xil bola SERVERDAN qidiriladi (audit, 2026-10-21).
  //
  // Ilgari taqqoslash ekranda turgan sahifaga qarardi, ya'ni uchinchi
  // sahifadagi bir xil bola ko'rinmasdi; va tug'ilgan sana TALAB
  // qilinardi, ya'ni sanasiz kiritilgan bola hech qachon
  // ogohlantirish bermasdi. Endi ism bo'yicha so'rov ketadi (`q` —
  // kirill/lotin farqini bilmaydigan kalit) va qaror qoidasi
  // `duplicates.ts` da.
  const nameForLookup = `${form.last_name ?? ''} ${form.first_name ?? ''}`.trim()
  const debouncedName = useDebouncedValue(nameForLookup)
  const lookupEnabled = !editing && Boolean(form.first_name?.trim() && form.last_name?.trim())
  const duplicateQuery = useQuery({
    queryKey: queryKeys.children(organizationId, { duplicateOf: debouncedName }),
    queryFn: () => childrenApi.list({ q: debouncedName, page_size: 25 }),
    enabled: lookupEnabled && debouncedName.length > 2,
    staleTime: 30_000,
  })
  const duplicate = lookupEnabled
    ? findDuplicate(duplicateQuery.data?.items ?? [], {
        first_name: form.first_name ?? '',
        last_name: form.last_name ?? '',
        date_of_birth: form.date_of_birth ?? '',
      })
    : null

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  // Tanlangan guruhning yosh oraligʻi — faqat ogohlantirish uchun.
  const ageMismatch = (() => {
    const group = (groupsQuery.data?.items ?? []).find((row) => row.id === formGroupId)
    if (!group) return null
    return ageOutsideGroup(group, form.date_of_birth ?? '')
  })()

  // Tarif bolani qo'shayotganda darhol biriktiriladi: tarifsiz bolaga
  // hisob-faktura chiqarib bo'lmaydi (docs/03 §13.3), ya'ni uni keyinroq
  // qo'shish — oy oxirida "nega bu bola hisobga tushmadi?" degan savol.
  const tariffsQuery = useQuery({
    queryKey: queryKeys.tariffs(organizationId),
    queryFn: tariffsApi.list,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'children'] })

  const handleError = (err: unknown) => {
    if (err instanceof ApiError) {
      setError(err.message)
      setFieldErrors(err.fieldErrors())
    } else {
      setError(t('Xatolik yuz berdi.'))
    }
  }

  /**
   * Guruh bolaning maydoni emas, alohida biriktirish — shuning uchun
   * saqlash IKKI chaqiruvdan iborat. Biriktirish alohida `try` ichida:
   * guruh to'lgan bo'lsa (sig'im chegarasi) bola baribir saqlanib qolsin
   * va foydalanuvchi "bola yo'qoldi" deb o'ylamasin — xabar ko'rsatiladi,
   * guruhni keyin tanlaydi.
   */
  const enrollIfChosen = async (childId: string, groupId: string) => {
    if (!groupId) return
    try {
      await childrenApi.enroll(childId, groupId)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('Xatolik.'))
    }
  }

  const createMutation = useMutation({
    mutationFn: async (
      payload: ChildInput & { groupId: string; guardian?: GuardianDraft; contract?: File | null },
    ) => {
      const { groupId, guardian, contract, ...childPayload } = payload
      const child = await childrenApi.create(childPayload)
      await enrollIfChosen(child.id, groupId)
      // Vasiy ixtiyoriy, lekin agar kiritilgan bo'lsa — DARHOL
      // biriktiriladi (PLAN 2.3). Ilgari uni ikkinchi ekranda qo'shish
      // kerak edi va ko'pincha unutilardi: vasiysiz bola esa SMS
      // olmaydigan bola.
      if (guardian?.phone) {
        await childrenApi.addGuardian(child.id, {
          first_name: guardian.first_name,
          last_name: guardian.last_name,
          phone: guardian.phone,
          ...(guardian.phone_alt ? { phone_alt: guardian.phone_alt } : {}),
          relation: guardian.relation,
          is_primary: true,
        })
      }
      // Shartnoma fayli — ixtiyoriy (2026-10-21). Yuklanmasa ham bola
      // saqlangan bo'ladi: xato alohida aytiladi, forma qayta yuborilmaydi
      // (aks holda bola ikki marta yaratilardi).
      if (contract) {
        try {
          await childrenApi.uploadDocument(child.id, contract)
        } catch (err) {
          toast(
            t('Bola saqlandi, lekin shartnoma fayli yuklanmadi: {reason}', {
              reason: err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'),
            }),
            'error',
          )
        }
      }
      return child
    },
    onSuccess: (child) => {
      closeForm()
      void invalidate()
      // Yaratilgach KARTAGA o'tiladi (PLAN 2.3): keyingi ish — tarif
      // biriktirish va to'lov qabul qilish — o'sha yerda.
      navigate(`/children/${child.id}`)
    },
    onError: handleError,
  })

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
      groupId,
    }: {
      id: string
      payload: Partial<ChildInput>
      groupId: string
    }) => {
      const child = await childrenApi.update(id, payload)
      if (groupId !== (editing?.current_group?.id ?? '')) await enrollIfChosen(id, groupId)
      return child
    },
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: handleError,
  })

  const saving = createMutation.isPending || updateMutation.isPending

  const submitForm = () => {
    const { payload: pricePayload, error: priceError } = priceToPayload(price)
    if (priceError) {
      setError(priceError)
      setFieldErrors((prev) => ({ ...prev, monthly_fee: priceError }))
      return
    }
    const body = { ...form, ...pricePayload }
    // Bo'sh qarz maydoni YUBORILMAYDI: bo'sh satr son emas va server uni
    // validatsiya xatosi bilan rad etardi. Tahrirlashda esa qarz umuman
    // yo'q — u faqat yaratishda ledger'ga yoziladi (PLAN 7.8).
    if (!body.opening_debt || editing) delete body.opening_debt
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload: body, groupId: formGroupId })
    } else {
      createMutation.mutate({
        ...body,
        branch_id: selectedBranchId,
        groupId: formGroupId,
        guardian: guardian.phone ? guardian : undefined,
        contract: contractFile,
      })
    }
  }

  const removeMutation = useMutation({ mutationFn: childrenApi.remove, onSuccess: invalidate })

  const enrollMutation = useMutation({
    mutationFn: ({ childId, groupId }: { childId: string; groupId: string }) =>
      childrenApi.enroll(childId, groupId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik.')),
  })

  const pagination = childrenQuery.data?.pagination
  const total = pagination?.count ?? 0
  const children = childrenQuery.data?.items ?? []

  const primaryGuardian = (child: Child) =>
    child.guardians.find((g) => g.is_primary) ?? child.guardians[0] ?? null

  // Jadval va kartochka bir xil hujayralarni ishlatadi — ikki qobiq,
  // bitta mazmun: tugma yoki holat o'zgarsa, ikkalasi birga o'zgaradi.
  // Bular KOMPONENT emas, render-funksiya: sahifa ichida yangi komponent
  // tipi yaratilsa React uni har renderda qayta o'rnatadi va `<Select>`
  // fokusi yo'qoladi.
  const renderName = (child: Child) => (
    <Link
      to={`/children/${child.id}`}
      className="group/name flex min-h-11 min-w-0 items-center gap-3"
    >
      <span
        className={cn(
          'grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold',
          avatarTone(child.full_name),
        )}
      >
        {initials(child.full_name)}
      </span>
      <span className="min-w-0">
        <span className="block truncate font-medium text-slate-800 transition-colors group-hover/name:text-brand-700">
          {child.last_name} {child.first_name}
        </span>
        {/* Bir xil ismli bolalarni AJRATADIGAN qator (audit,
            2026-10-21): otasining ismi, tugʻilgan sana va shartnoma
            raqami. Ilgari faqat otasining ismi turardi va u koʻpincha
            boʻsh. */}
        <span className="block truncate text-xs text-slate-500">
          {[child.middle_name, formatDate(child.date_of_birth), child.contract_number]
            .filter(Boolean)
            .join(' · ')}
        </span>
      </span>
    </Link>
  )

  /**
   * Tugagan sinov ALOHIDA koʻrinadi (mijoz soʻrovi, 2026-10-28):
   * unutilgan belgi pul yoʻqotadi — sinovdagi bolaga hisob-faktura
   * yozilmaydi, ya'ni "sinovda" boʻlib qolgan bola oylab bepul qatnaydi.
   */
  const renderStatus = (child: Child) => {
    const status = child.enrollment_status
    const enrolled = status === 'active' || status === 'returned'
    const expired = status === 'trial' && child.trial_is_over
    return (
      <span
        className={cn(
          'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
          expired
            ? 'bg-orik-50 text-orik-700'
            : enrolled
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-slate-100 text-slate-600',
        )}
      >
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            expired ? 'bg-orik-500' : enrolled ? 'bg-emerald-500' : 'bg-slate-400',
          )}
        />
        {expired ? t('Sinov tugadi') : (STATUS_LABELS[status] ?? status)}
      </span>
    )
  }

  const renderGroup = (child: Child) =>
    can('children.update') ? (
      <Select
        aria-label={t('Guruh')}
        value={child.current_group?.id ?? ''}
        onChange={(e) => e.target.value && setPendingGroup({ child, groupId: e.target.value })}
        size="sm"
        className="max-w-[180px]"
      >
        <GroupOptions groups={groupsQuery.data?.items ?? []} currentId={child.current_group?.id} />
      </Select>
    ) : (
      <span className="text-sm text-slate-600">{child.current_group?.name ?? '—'}</span>
    )

  const renderActions = (child: Child) => (
    <div className="flex items-center justify-end gap-1">
      {can('children.update') && (
        <button
          type="button"
          onClick={() => openEdit(child)}
          className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
          title={t('Tahrirlash')}
          aria-label={t('Tahrirlash')}
        >
          <Pencil className="h-4 w-4" />
        </button>
      )}
      {can('children.delete') && (
        <button
          type="button"
          onClick={() => removeMutation.mutate(child.id)}
          className="rounded-lg p-2 text-slate-500 transition hover:bg-red-50 hover:text-red-600"
          title={t('Arxivga oʻtkazish')}
          aria-label={t('Arxivga oʻtkazish')}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <ConfirmDialog
        open={pendingGroup !== null}
        title={t('Guruhni oʻzgartirish')}
        body={t('{name}: {from} guruhidan {to} guruhiga', {
          name: pendingGroup?.child.full_name ?? '',
          from: pendingGroup?.child.current_group?.name ?? t('guruhsiz'),
          to:
            groupsQuery.data?.items.find((g) => g.id === pendingGroup?.groupId)?.name ??
            t('guruhsiz'),
        })}
        busy={enrollMutation.isPending}
        onCancel={() => setPendingGroup(null)}
        onConfirm={() => {
          if (pendingGroup) {
            enrollMutation.mutate({
              childId: pendingGroup.child.id,
              groupId: pendingGroup.groupId,
            })
          }
          setPendingGroup(null)
        }}
      />

      {showImport && <ImportWizard onClose={() => setShowImport(false)} />}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Bolalar')}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {total > 0 ? t('Jami {total} ta bola', { total }) : t('Roʻyxat boʻsh')}
          </p>
        </div>
        <div className="flex w-full gap-2 sm:w-auto">
          {can('children.create') && (
            <>
              <button
                type="button"
                onClick={() => setShowImport(true)}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 sm:flex-none"
              >
                <Upload className="h-4 w-4" />
                {t('Import')}
              </button>
              <button
                type="button"
                onClick={openCreate}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 sm:flex-none"
              >
                <Plus className="h-4 w-4" />
                {t('Bola qoʻshish')}
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {showForm && can(editing ? 'children.update' : 'children.create') && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            submitForm()
          }}
          className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2"
        >
          <h2 className="text-sm font-semibold text-slate-800 sm:col-span-2">
            {editing
              ? t('{full_name} — tahrirlash', { full_name: editing.full_name })
              : t('Yangi bola')}
          </h2>

          {(
            [
              ['last_name', t('Familiya'), 'text'],
              ['first_name', t('Ism'), 'text'],
              ['middle_name', t('Otasining ismi'), 'text'],
              ['date_of_birth', t('Tugʻilgan sana'), 'date'],
            ] as const
          ).map(([key, label, type]) => (
            <div key={key}>
              <FieldLabel htmlFor={key} required={key !== 'middle_name'}>
                {label}
              </FieldLabel>
              {/* Sana — `DateInput` (05 §17.1), native `type=date` EMAS.
                  Brauzerning oʻz maydoni amerikacha tartibni
                  (`mm/dd/yyyy`) koʻrsatadi va bogʻcha xodimi uni
                  teskari oʻqiydi. Bu qoida hujjatda bor edi, lekin
                  aynan eng koʻp ishlatiladigan formada buzilgan — buni
                  brauzerdagi E2E topdi. */}
              {type === 'date' ? (
                <DateInput
                  id={key}
                  required
                  value={(form[key] as string) ?? ''}
                  onChange={(iso) => setForm((p) => ({ ...p, [key]: iso }))}
                />
              ) : (
                <input
                  id={key}
                  type={type}
                  required={key !== 'middle_name'}
                  value={(form[key] as string) ?? ''}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className={cn(
                    'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2',
                    fieldErrors[key]
                      ? 'border-red-300 focus:ring-red-100'
                      : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
                  )}
                />
              )}
              {fieldErrors[key] && <p className="mt-1 text-xs text-red-600">{fieldErrors[key]}</p>}
            </div>
          ))}

          {/* Yangi yoki mavjud mijoz (PLAN 7.8). Tanlov ikki narsani
              hal qiladi: birinchi oy proporsional hisoblanadimi va
              bolaning eski qarzi bormi. */}
          {!editing && (
            <div>
              <span className="mb-1 block text-xs font-medium text-slate-600">{t('Mijoz')}</span>
              <div role="group" className="grid grid-cols-2 gap-2">
                {(
                  [
                    [false, t('Yangi mijoz'), t('Birinchi oy ish kunlari boʻyicha')],
                    [true, t('Mavjud mijoz'), t('Allaqachon qatnab yuradi')],
                  ] as const
                ).map(([value, label, hint]) => (
                  <button
                    key={label}
                    type="button"
                    aria-pressed={Boolean(form.is_existing_client) === value}
                    onClick={() =>
                      setForm((p) => ({
                        ...p,
                        is_existing_client: value,
                        opening_debt: value ? p.opening_debt : '',
                      }))
                    }
                    className={cn(
                      'rounded-lg border px-3 py-2 text-left transition',
                      Boolean(form.is_existing_client) === value
                        ? 'border-brand-500 bg-brand-50/60'
                        : 'border-slate-200 hover:border-slate-300',
                    )}
                  >
                    <span className="block text-sm font-medium text-slate-900">{label}</span>
                    <span className="block text-xs text-slate-500">{hint}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Sinov muddati (Bosqich 12.1): yangi bolaning birinchi ish
              kunlari bepul — sozlamada nechta ekani. Kelishuv bo'lsa, shu
              yerda o'chiriladi va to'lov birinchi kundan boshlanadi. */}
          {!editing && !form.is_existing_client && (
            <label className="flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={Boolean(form.skip_trial)}
                onChange={(e) => setForm((p) => ({ ...p, skip_trial: e.target.checked }))}
                className="mt-0.5 h-4 w-4 rounded border-slate-300 focus-visible:ring-2 focus-visible:ring-brand-500"
              />
              <span>
                <span className="block font-medium">{t('Sinov muddatisiz')}</span>
                <span className="block text-xs text-slate-500">
                  {t('Toʻlov birinchi kundan boshlanadi — bepul sinov kunlari qoʻllanmaydi.')}
                </span>
              </span>
            </label>
          )}

          {!editing && form.is_existing_client && (
            <div>
              <label
                htmlFor="opening_debt"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Eski qarz')}
              </label>
              <input
                id="opening_debt"
                inputMode="numeric"
                placeholder="0"
                value={form.opening_debt ?? ''}
                onChange={(e) =>
                  setForm((p) => ({ ...p, opening_debt: e.target.value.replace(/\D/g, '') }))
                }
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
              <p className="mt-1 text-xs text-slate-500">
                {t(
                  'Qarz boʻlmasa boʻsh qoldiring. Kiritilsa, bola qarzdorlar roʻyxatida koʻrinadi.',
                )}
              </p>
            </div>
          )}

          {/* Qogʻozdagi shartnoma raqami (PLAN 9.3) — tizim tuzadigan
              shartnomaning raqami bundan alohida. */}
          <div>
            <label
              htmlFor="contract_number"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Shartnoma raqami')}
            </label>
            <input
              id="contract_number"
              maxLength={40}
              value={form.contract_number ?? ''}
              onChange={(e) => setForm((p) => ({ ...p, contract_number: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              placeholder={t('Masalan: 2026/112')}
            />
          </div>

          <div>
            <FieldLabel htmlFor="enrolled_on" required={!editing}>
              {t('Qabul sanasi')}
            </FieldLabel>
            <DateInput
              id="enrolled_on"
              required={!editing}
              value={form.enrolled_on ?? ''}
              onChange={(iso) => setForm((p) => ({ ...p, enrolled_on: iso }))}
            />
            <p className="mt-1 text-xs text-slate-500">
              {t('Birinchi oy shu sanadan boshlab, ish kunlari boʻyicha hisoblanadi.')}
            </p>
          </div>

          <div>
            <label htmlFor="gender" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Jinsi')}
            </label>
            <Select
              id="gender"
              value={form.gender}
              onChange={(e) =>
                setForm((p) => ({ ...p, gender: e.target.value as 'male' | 'female' }))
              }
              className="w-full"
            >
              <option value="male">{t('Oʻgʻil bola')}</option>
              <option value="female">{t('Qiz bola')}</option>
            </Select>
          </div>

          {/* Bosqich 14: oila bogʻcha haqida qayerdan eshitgan — statistika
              uchun. Yangi bolada majburiy; eski bolada boʻsh qolishi mumkin. */}
          <div>
            <FieldLabel htmlFor="heard_from" required={!editing}>
              {t('Bizni qayerdan eshitgan?')}
            </FieldLabel>
            <Select
              id="heard_from"
              required={!editing}
              value={form.heard_from ?? ''}
              onChange={(e) => setForm((p) => ({ ...p, heard_from: e.target.value }))}
              className="w-full"
            >
              <option value="">{editing ? t('Koʻrsatilmagan') : t('Tanlang')}</option>
              {HEARD_FROM.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </div>
          {form.heard_from === 'other' && (
            <div>
              <label
                htmlFor="heard_from_note"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Qayerdan — aniqroq')}
              </label>
              <input
                id="heard_from_note"
                maxLength={120}
                value={form.heard_from_note ?? ''}
                onChange={(e) => setForm((p) => ({ ...p, heard_from_note: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>
          )}

          {/* Guruh va tarif — AYNAN shu yerda, qo'shish paytida.
              Ilgari ular ro'yxatdan va bola kartasidan alohida
              qo'yilardi: 40 ta bola kiritgan odam har biri uchun yana
              ikki joyga qaytishi kerak edi, tarifsiz qolgan bola esa
              oy oxirida hisob-fakturasiz qolardi. */}
          <div>
            <label htmlFor="form-group" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Guruh')}
            </label>
            <Select
              id="form-group"
              value={formGroupId}
              onChange={(e) => setFormGroupId(e.target.value)}
              className="w-full"
            >
              <GroupOptions groups={groupsQuery.data?.items ?? []} />
            </Select>
            {/* Yosh oraligʻi BLOKLAMAYDI, ogohlantiradi (audit,
                2026-10-21): bogʻchada aka-ukani bir guruhda qoldirish
                yoki joy yoʻqligi kabi istisnolar koʻp. */}
            {ageMismatch && (
              <p className="mt-1 text-xs text-orik-700">
                {ageMismatch.min !== null && ageMismatch.max !== null
                  ? t('Bola {age} yoshda, guruh esa {min}–{max} yosh uchun.', { ...ageMismatch })
                  : ageMismatch.max !== null
                    ? t('Bola {age} yoshda, guruh esa {max} yoshgacha.', { ...ageMismatch })
                    : t('Bola {age} yoshda, guruh esa {min} yoshdan.', { ...ageMismatch })}
              </p>
            )}
          </div>

          <div>
            <p className="mb-1 block text-xs font-medium text-slate-600">{t('Oylik narx')}</p>
            <PricePicker
              idPrefix="form"
              value={price}
              onChange={(next) => {
                setPrice(next)
                setFieldErrors(({ monthly_fee: _drop, ...rest }) => rest)
              }}
              tariffs={tariffsQuery.data?.items ?? []}
            />
            {fieldErrors.monthly_fee && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.monthly_fee}</p>
            )}
          </div>

          {/* Imzolangan shartnoma fayli — IXTIYORIY (2026-10-21). */}
          {!editing && (
            <div className="sm:col-span-2">
              <label
                htmlFor="contract-file"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Shartnoma fayli (ixtiyoriy) — PDF, DOC yoki DOCX')}
              </label>
              <input
                id="contract-file"
                type="file"
                accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null
                  const problem = file ? documentProblem(file) : null
                  setFieldErrors(({ contract: _drop, ...rest }) =>
                    problem ? { ...rest, contract: problem } : rest,
                  )
                  setContractFile(problem ? null : file)
                  if (problem) event.target.value = ''
                }}
                className="block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
              />
              {fieldErrors.contract && (
                <p className="mt-1 text-xs text-red-600">{fieldErrors.contract}</p>
              )}
            </div>
          )}

          {/* Vasiy — IXTIYORIY, lekin shu yerda (PLAN 2.3).
              Ilgari uni ikkinchi ekranda qo'shish kerak edi va
              ko'pincha unutilardi; vasiysiz bola esa SMS olmaydigan
              bola — ya'ni eslatma ham, kvitansiya ham bormaydi. */}
          {!editing && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 sm:col-span-2">
              <p className="text-xs font-semibold text-slate-700">{t('Vasiy (ixtiyoriy)')}</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-4">
                <input
                  aria-label={t('Vasiy familiyasi')}
                  placeholder={t('Familiya')}
                  value={guardian.last_name}
                  onChange={(e) => setGuardian((p) => ({ ...p, last_name: e.target.value }))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                <input
                  aria-label={t('Vasiy ismi')}
                  placeholder={t('Ism')}
                  value={guardian.first_name}
                  onChange={(e) => setGuardian((p) => ({ ...p, first_name: e.target.value }))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                <input
                  aria-label={t('Vasiy telefoni')}
                  type="tel"
                  placeholder="+998 90 123 45 67"
                  value={guardian.phone}
                  onChange={(e) => setGuardian((p) => ({ ...p, phone: e.target.value }))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                {showGuardianAlt ? (
                  <input
                    aria-label={t('Ikkinchi raqam')}
                    type="tel"
                    placeholder={t('Ikkinchi raqam')}
                    value={guardian.phone_alt}
                    onChange={(e) => setGuardian((p) => ({ ...p, phone_alt: e.target.value }))}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowGuardianAlt(true)}
                    className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm text-brand-600 hover:border-brand-300"
                  >
                    {t('+ Ikkinchi raqam')}
                  </button>
                )}
                <Select
                  aria-label={t('Kim boʻladi')}
                  value={guardian.relation}
                  onChange={(e) => setGuardian((p) => ({ ...p, relation: e.target.value }))}
                >
                  <option value="mother">{t('Onasi')}</option>
                  <option value="father">{t('Otasi')}</option>
                  <option value="other">{t('Boshqa')}</option>
                </Select>
              </div>
            </div>
          )}

          {/* Dublikat ogohlantirishi (PLAN 2.3) — to'sib qo'ymaydi:
              egizaklarda ism va tug'ilgan sana haqiqatan bir xil
              bo'lishi mumkin. Sana noma'lum bo'lsa ogohlantirish
              yo'qolmaydi, faqat ohangi yumshaydi (audit, 2026-10-21). */}
          {duplicate && (
            <p className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-800 sm:col-span-2">
              {duplicate.certainty === 'same_birth_date'
                ? t('Shunday ism va tugʻilgan sanali bola allaqachon bor: {name}', {
                    name: duplicate.child.full_name,
                  })
                : t(
                    'Shunday ismli bola allaqachon bor: {name} — tugʻilgan sanasi koʻrsatilmagan.',
                    {
                      name: duplicate.child.full_name,
                    },
                  )}
            </p>
          )}

          <div className="flex gap-2 sm:col-span-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {saving ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <div className="relative flex-1 sm:min-w-[220px] sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('Ism, shartnoma raqami yoki ID…')}
            aria-label={t('Ism, shartnoma raqami yoki ID…')}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        {/* Tanlagich endi sukut boʻyicha `w-full`: eni berilmasa, u
            qatorni toʻliq egallab, qidiruv maydonini pastga surib
            yuboradi. */}
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label={t('Holat')}
          className="sm:max-w-[14rem]"
        >
          <option value="">{t('Barcha holatlar')}</option>
          {STATUS_ORDER.map((value) => (
            <option key={value} value={value}>
              {STATUS_LABELS[value]}
            </option>
          ))}
        </Select>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {childrenQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-500">{t('Yuklanmoqda…')}</p>
        )}
        {childrenQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {childrenQuery.error instanceof ApiError
              ? childrenQuery.error.message
              : t('Maʼlumotni yuklab boʻlmadi.')}
          </p>
        )}
        {childrenQuery.data && children.length === 0 && (
          <div className="px-4 py-12 text-center">
            <Users className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">
              {debouncedSearch || statusFilter
                ? t('Shartga mos bola topilmadi.')
                : t('Hozircha bola yoʻq.')}
            </p>
            {can('children.create') && !debouncedSearch && !statusFilter && (
              <button
                type="button"
                onClick={() => setShowImport(true)}
                className="mt-3 text-sm font-medium text-brand-600 hover:underline"
              >
                {t('Excel/CSV dan import qilish')}
              </button>
            )}
          </div>
        )}

        {children.length > 0 && (
          <div
            className={cn('transition-opacity', childrenQuery.isPlaceholderData && 'opacity-60')}
          >
            {/* Jadval — planshet va undan keng ekranlar. */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="border-b border-slate-100 bg-slate-50/70 text-left text-xs uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t('Bola')}</th>
                    <th className="px-4 py-3 font-medium">{t('Yosh')}</th>
                    <th className="px-4 py-3 font-medium">{t('Guruh')}</th>
                    <th className="px-4 py-3 font-medium">{t('Vasiy')}</th>
                    <th className="px-4 py-3 font-medium">{t('Holat')}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {children.map((child) => {
                    const primary = primaryGuardian(child)
                    return (
                      <tr key={child.id} className="transition-colors hover:bg-slate-50/70">
                        <td className="px-4 py-3">{renderName(child)}</td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-600 tabular-nums">
                          {t('{age_years} yosh', { age_years: child.age_years })}
                        </td>
                        <td className="px-4 py-3">{renderGroup(child)}</td>
                        <td className="px-4 py-3 text-slate-600">
                          {primary ? (
                            <>
                              <p className="truncate">{primary.guardian.full_name}</p>
                              <a
                                href={`tel:${primary.guardian.phone}`}
                                className="mt-0.5 inline-flex min-h-[24px] items-center gap-1 py-0.5 text-xs text-slate-500 transition-colors hover:text-brand-600"
                              >
                                <Phone className="h-3 w-3" />
                                {primary.guardian.phone}
                              </a>
                            </>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3">{renderStatus(child)}</td>
                        <td className="px-4 py-3">{renderActions(child)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Kartochkalar — telefon. Gorizontal skroll jadvali barmoq
                bilan ishlatib bo'lmaydigan darajada tor bo'lardi. */}
            <ul className="divide-y divide-slate-100 md:hidden">
              {children.map((child) => {
                const primary = primaryGuardian(child)
                return (
                  <li key={child.id} className="space-y-3 px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      {renderName(child)}
                      {renderStatus(child)}
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-500">
                      <p>
                        <span className="text-slate-500">{t('Yosh:')}</span>{' '}
                        <span className="text-slate-700 tabular-nums">{child.age_years}</span>
                      </p>
                      <p className="truncate">
                        <span className="text-slate-500">{t('Vasiy:')}</span>{' '}
                        <span className="text-slate-700">{primary?.guardian.full_name ?? '—'}</span>
                      </p>
                      {primary && (
                        <a
                          href={`tel:${primary.guardian.phone}`}
                          className="col-span-2 inline-flex min-h-[24px] items-center gap-1 py-0.5 text-slate-500 hover:text-brand-600"
                        >
                          <Phone className="h-3 w-3" />
                          {primary.guardian.phone}
                        </a>
                      )}
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      {renderGroup(child)}
                      {renderActions(child)}
                    </div>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {pagination && (
          <Pagination
            page={pagination.page}
            totalPages={pagination.total_pages}
            count={pagination.count}
            pageSize={pagination.page_size}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        )}
      </div>
    </div>
  )
}
