/**
 * Frozen product modules (owner's decision, 2026-10-03).
 *
 * Contracts and the kitchen are built but switched off; the backend decides
 * (`FEATURE_*` in `.env`) and says so in `/auth/me` → `user.features`. One
 * switch for both sides: the screens appear exactly when the endpoints do.
 */

import { useAuth } from '@/app/providers/AuthProvider'

export type Feature = 'contracts' | 'kitchen'

export function useFeature(feature: Feature): boolean {
  const { user } = useAuth()
  return Boolean(user?.features?.includes(feature))
}
