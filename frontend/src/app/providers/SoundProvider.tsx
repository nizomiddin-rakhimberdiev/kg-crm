import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { installGlobalClickSound, isMuted, setMuted, playSound } from '@/lib/sound'

interface SoundContextValue {
  muted: boolean
  toggle: () => void
}

const SoundContext = createContext<SoundContextValue>({ muted: false, toggle: () => {} })

export function useSound(): SoundContextValue {
  return useContext(SoundContext)
}

export function SoundProvider({ children }: { children: ReactNode }) {
  const [muted, setMutedState] = useState<boolean>(isMuted())

  useEffect(() => {
    installGlobalClickSound()
  }, [])

  const toggle = () => {
    const next = !muted
    setMuted(next)
    setMutedState(next)
    if (!next) playSound('toggle') // small confirmation when turning sound back on
  }

  return <SoundContext.Provider value={{ muted, toggle }}>{children}</SoundContext.Provider>
}
