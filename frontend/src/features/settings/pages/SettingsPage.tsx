import { useState, type FC } from 'react'
import {
  Building2,
  ShieldCheck,
  CreditCard,
  MessageSquare,
  Bell,
  Lock,
  UserCog,
  Save,
  type LucideIcon,
} from 'lucide-react'
import { Card, PageHeader, Button } from '@/components/ui/primitives'
import { cn } from '@/lib/utils'
import {
  OrgTab,
  RolesTab,
  PaymentsTab,
  SmsTab,
  AppearanceTab,
  SecurityTab,
  ProfileTab,
} from '../components/tabs'

interface Tab {
  key: string
  label: string
  icon: LucideIcon
  component: FC
}

const tabs: Tab[] = [
  { key: 'org', label: "Muassasa Ma'lumotlari", icon: Building2, component: OrgTab },
  { key: 'roles', label: 'Rollar va Huquqlar', icon: ShieldCheck, component: RolesTab },
  { key: 'payments', label: "To'lov Tizimlari", icon: CreditCard, component: PaymentsTab },
  { key: 'sms', label: 'SMS Xabarnomalar', icon: MessageSquare, component: SmsTab },
  { key: 'appearance', label: "Ko'rinish va Bildirishnomalar", icon: Bell, component: AppearanceTab },
  { key: 'security', label: 'Xavfsizlik', icon: Lock, component: SecurityTab },
  { key: 'profile', label: 'Profil Sozlamalari', icon: UserCog, component: ProfileTab },
]

export default function SettingsPage() {
  const [active, setActive] = useState('org')
  const current = tabs.find((t) => t.key === active)!
  const ActiveTab = current.component

  return (
    <div className="space-y-6">
      <PageHeader title="Tizim Sozlamalari">
        <Button icon={Save} data-sound="success" data-toast={`${current.label} saqlandi ✓`}>
          Saqlash
        </Button>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Sub-nav */}
        <Card className="h-fit p-2">
          <nav className="space-y-1">
            {tabs.map((t) => (
              <button
                key={t.key}
                data-sound="nav"
                onClick={() => setActive(t.key)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  active === t.key
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
                )}
              >
                <t.icon
                  className={cn('w-[18px] h-[18px]', active === t.key ? 'text-brand-600' : 'text-slate-400')}
                />
                {t.label}
              </button>
            ))}
          </nav>
        </Card>

        {/* Active tab content */}
        <Card className="p-6">
          <ActiveTab />
        </Card>
      </div>
    </div>
  )
}
