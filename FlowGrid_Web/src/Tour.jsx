import { useState, useEffect, useLayoutEffect } from 'react'

// Floating step-by-step guided tour -- spotlights one element at a time with
// a title/text pair supplied by the caller (steps are page-specific, so each
// page mounts its own <Tour steps={...} /> and it auto-starts fresh every
// time that page is visited, not just the first time). Same spotlight
// pattern as the PPO app's tour.js, reimplemented as a React component
// since this app has no shared vanilla-JS layer to hook into.
export default function Tour({ steps }) {
  const [current, setCurrent] = useState(0)
  const [active, setActive] = useState(false)
  const [rect, setRect] = useState(null)

  const validSteps = steps.filter(s => s.target?.current)
  const step = validSteps[current]

  // Deliberately does not gate on "are there valid steps yet": refs can be
  // transiently null for a render or two (React StrictMode's dev-only
  // mount/unmount/remount check detaches and reattaches them), and a
  // closure captured at that instant would wrongly latch onto zero steps
  // forever. The render guard below (!step) already handles "not ready" by
  // rendering nothing; once a later render sees populated refs, it shows.
  useEffect(() => {
    const t = setTimeout(() => setActive(true), 500)
    return () => clearTimeout(t)
  }, [])

  useLayoutEffect(() => {
    if (!active || !step) return undefined
    const update = () => setRect(step.target.current?.getBoundingClientRect() || null)
    update()
    step.target.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
    }
  }, [active, step])

  const next = () => {
    if (current >= validSteps.length - 1) setActive(false)
    else setCurrent(c => c + 1)
  }
  const prev = () => setCurrent(c => Math.max(0, c - 1))

  useEffect(() => {
    if (!active) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setActive(false)
      else if (e.key === 'ArrowRight') next()
      else if (e.key === 'ArrowLeft') prev()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, current])

  if (!active || !step || !rect) return null

  const pad = 8
  const tooltipWidth = 340
  const tooltipHeight = 220
  let top = rect.bottom + pad + 12
  if (top + tooltipHeight > window.innerHeight - 12) {
    top = Math.max(12, rect.top - pad - tooltipHeight - 12)
  }
  let left = Math.min(rect.left, window.innerWidth - tooltipWidth - 12)
  left = Math.max(12, left)

  return (
    <>
      <div
        style={{
          position: 'fixed',
          zIndex: 9998,
          top: rect.top - pad,
          left: rect.left - pad,
          width: rect.width + pad * 2,
          height: rect.height + pad * 2,
          borderRadius: 14,
          pointerEvents: 'none',
          boxShadow: '0 0 0 9999px rgba(10, 8, 30, 0.6), 0 0 0 2px var(--color-accent)',
          transition: 'top 0.25s ease, left 0.25s ease, width 0.25s ease, height 0.25s ease',
        }}
      />
      <div
        style={{
          position: 'fixed',
          zIndex: 9999,
          top,
          left,
          width: tooltipWidth,
          maxWidth: 'calc(100vw - 24px)',
          background: 'var(--color-bg-alt)',
          border: '1px solid var(--color-border)',
        }}
        className="rounded-2xl p-5 shadow-card"
      >
        <p className="text-xs font-bold text-accent uppercase tracking-wide mb-1">
          Step {current + 1} of {validSteps.length}
        </p>
        <h3 className="text-text font-bold mb-2">{step.title}</h3>
        <p className="text-sm text-muted mb-4 leading-relaxed">{step.text}</p>
        <div className="flex items-center justify-between gap-2">
          <button type="button" onClick={() => setActive(false)} className="text-xs text-muted hover:text-text">
            Skip guide
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={prev}
              disabled={current === 0}
              className="px-3 py-1.5 rounded-lg text-sm glass-subtle text-muted disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button type="button" onClick={next} className="px-3 py-1.5 rounded-lg text-sm bg-accent text-white font-semibold">
              {current === validSteps.length - 1 ? 'Done' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
