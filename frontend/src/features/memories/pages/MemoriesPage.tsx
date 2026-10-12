/**
 * Radix AI — rasm xotirasi, yuz tanish, Telegram bot va kamera nazorati.
 * Bitta ekran, beshta bo'lim; har bir bo'lim o'z ruxsati bilan (backend ham tekshiradi).
 */

import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { CalendarClock, Eye, Images, Send, ShieldCheck, Siren } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { PageHeader } from '@/components/ui/primitives'
import { queryKeys } from '@/lib/api/queryKeys'
import { t } from '@/lib/i18n'
import { eventsApi } from '../api'
import { ConsentPanel } from '../components/ConsentPanel'
import { PhotosPanel } from '../components/PhotosPanel'
import { SafetyPanel } from '../components/SafetyPanel'
import { SurveillancePanel } from '../components/SurveillancePanel'
import { SchedulePanel } from '../components/SchedulePanel'
import { TelegramPanel } from '../components/TelegramPanel'
import { Tabs } from '../components/shared'
import { EASE } from '../motion'

type TabId = 'photos' | 'safety' | 'watch' | 'schedule' | 'telegram' | 'consent'

export default function MemoriesPage({
  initialTab = 'photos',
  cameras = false,
}: {
  initialTab?: TabId
  /** Sidebar'dagi "Kameralar" punkti: sarlavha kamera haqida bo'ladi. */
  cameras?: boolean
}) {
  const organizationId = useOrganizationId()
  const reduce = useReducedMotion()
  const [tab, setTab] = useState<TabId>(initialTab)

  // Yangi hodisalar soni tab ustida qizil nishon sifatida ko'rinadi.
  const newEvents = useQuery({
    queryKey: queryKeys.cameraEvents(organizationId, { status: 'new', page_size: 1 }),
    queryFn: () => eventsApi.list({ status: 'new', page_size: 1 }),
    refetchInterval: 30_000,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title={cameras ? t('Kameralar') : t('Radix AI')}
        subtitle={
          cameras
            ? t("Kamerani ulang (RTSP, NVR, webhook), holatini va hodisalarni kuzating.")
            : t("Rasm xotirasi, yuz tanish, Telegram bot va kamera nazorati.")
        }
      />

      <Tabs<TabId>
        value={tab}
        onChange={setTab}
        tabs={[
          { id: 'photos', label: t('Rasmlar'), icon: <Images className="h-4 w-4" /> },
          {
            id: 'safety',
            label: t('Xavfsizlik'),
            icon: <Siren className="h-4 w-4" />,
            badge: newEvents.data?.pagination?.count ?? 0,
          },
          { id: 'watch', label: t('Kuzatuv'), icon: <Eye className="h-4 w-4" /> },
          { id: 'schedule', label: t('Kun tartibi'), icon: <CalendarClock className="h-4 w-4" /> },
          { id: 'telegram', label: t('Telegram'), icon: <Send className="h-4 w-4" /> },
          { id: 'consent', label: t('Yuz roziligi'), icon: <ShieldCheck className="h-4 w-4" /> },
        ]}
      />

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={tab}
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduce ? undefined : { opacity: 0, y: -8 }}
          transition={{ duration: 0.22, ease: EASE }}
        >
          {tab === 'photos' && <PhotosPanel />}
          {tab === 'safety' && <SafetyPanel />}
          {tab === 'watch' && <SurveillancePanel />}
          {tab === 'schedule' && <SchedulePanel />}
          {tab === 'telegram' && <TelegramPanel />}
          {tab === 'consent' && <ConsentPanel />}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
