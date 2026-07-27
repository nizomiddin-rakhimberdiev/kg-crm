/**
 * Soft sound engine (Web Audio API) — synthesised, no audio files.
 *
 * Design goals: even at full volume the sounds must feel gentle and pleasant
 * (a kindergarten office, not an arcade). We use pure SINE waves through a
 * LOW-PASS filter with a soft attack + natural decay, tuned to musical notes.
 */

export type SoundType = 'click' | 'nav' | 'toggle' | 'open' | 'success' | 'error'

let ctx: AudioContext | null = null
let master: GainNode | null = null
let muted = typeof localStorage !== 'undefined' && localStorage.getItem('kg-sound-muted') === '1'
let installed = false

function audioCtx(): AudioContext {
  if (!ctx) {
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    ctx = new AC()
  }
  return ctx
}

/** A shared, gentle master bus: soft overall level + warm low-pass so nothing
 *  is ever harsh, however "loud" the tones are. */
function masterBus(ac: AudioContext): GainNode {
  if (!master) {
    master = ac.createGain()
    master.gain.value = 0.55 // keeps everything soft
    const warm = ac.createBiquadFilter()
    warm.type = 'lowpass'
    warm.frequency.value = 2400 // rolls off harsh highs
    warm.Q.value = 0.2
    master.connect(warm)
    warm.connect(ac.destination)
  }
  return master
}

export function isMuted(): boolean {
  return muted
}

export function setMuted(value: boolean): void {
  muted = value
  try {
    localStorage.setItem('kg-sound-muted', value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

interface Note {
  freq: number
  dur: number
  peak: number
  attack?: number
  filter?: number
  slideTo?: number
  delay?: number
}

/** Play one soft note: sine → low-pass → gentle envelope → master bus. */
function note(ac: AudioContext, n: Note): void {
  const t0 = ac.currentTime + (n.delay ?? 0)
  const attack = n.attack ?? 0.02

  const osc = ac.createOscillator()
  osc.type = 'sine'
  osc.frequency.setValueAtTime(n.freq, t0)
  if (n.slideTo) osc.frequency.linearRampToValueAtTime(n.slideTo, t0 + n.dur)

  const lp = ac.createBiquadFilter()
  lp.type = 'lowpass'
  lp.frequency.value = n.filter ?? 2000
  lp.Q.value = 0.2

  const gain = ac.createGain()
  gain.gain.setValueAtTime(0.0001, t0)
  gain.gain.linearRampToValueAtTime(n.peak, t0 + attack) // soft fade-in (no click)
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + n.dur) // natural fade-out

  osc.connect(lp)
  lp.connect(gain)
  gain.connect(masterBus(ac))
  osc.start(t0)
  osc.stop(t0 + n.dur + 0.03)
}

// Musical notes (Hz): C5=523, D5=587, E5=659, G5=784, A4=440, G4=392, D4=294
const presets: Record<SoundType, Note[]> = {
  // gentle rounded "tock"
  click: [{ freq: 523, dur: 0.13, peak: 0.5, filter: 1700 }],
  // soft confirm blip
  toggle: [{ freq: 587, dur: 0.14, peak: 0.5, filter: 1900 }],
  // opening a menu — light upward glide
  open: [{ freq: 440, dur: 0.16, peak: 0.42, filter: 2200, slideTo: 660 }],
  // navigation — two soft rising notes
  nav: [
    { freq: 523, dur: 0.15, peak: 0.42, filter: 2000 },
    { freq: 659, dur: 0.18, peak: 0.42, filter: 2200, delay: 0.07 },
  ],
  // success — pleasant 3-note major arpeggio (C–E–G), bell-like
  success: [
    { freq: 523, dur: 0.18, peak: 0.5, filter: 2400 },
    { freq: 659, dur: 0.2, peak: 0.5, filter: 2400, delay: 0.1 },
    { freq: 784, dur: 0.28, peak: 0.5, filter: 2600, delay: 0.2 },
  ],
  // error — soft, mellow downward pair (never harsh)
  error: [
    { freq: 392, dur: 0.18, peak: 0.45, filter: 1300 },
    { freq: 294, dur: 0.26, peak: 0.45, filter: 1200, delay: 0.11 },
  ],
}

export function playSound(type: SoundType = 'click'): void {
  if (muted) return
  let ac: AudioContext
  try {
    ac = audioCtx()
  } catch {
    return
  }
  if (ac.state === 'suspended') void ac.resume() // unlock on first user gesture
  for (const n of presets[type]) note(ac, n)
}

/**
 * One global listener → EVERY interactive element makes a sound on press.
 * Override the sound with `data-sound="success|error|nav|toggle|open"`.
 */
export function installGlobalClickSound(): void {
  if (installed || typeof document === 'undefined') return
  installed = true
  document.addEventListener(
    'pointerdown',
    (e) => {
      const target = e.target as HTMLElement | null
      if (!target || !target.closest) return
      const el = target.closest(
        'button, a, [role="button"], [role="option"], [role="tab"], label, select, input[type="checkbox"], input[type="radio"], [data-sound]',
      ) as HTMLElement | null
      if (!el || el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true') return
      const custom = el.getAttribute('data-sound') as SoundType | null
      playSound(custom ?? 'click')
    },
    true,
  )
}
