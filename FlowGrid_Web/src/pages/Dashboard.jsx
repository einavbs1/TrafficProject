import { useState, useEffect, useRef } from 'react'
import { Clock, Car, Lightbulb, Activity, Circle, Play } from 'lucide-react'
import { useJunction, LIVE_JUNCTION_ID } from '../JunctionContext'
import Tour from '../Tour'

const PPO_API = 'http://127.0.0.1:8001'

function generateMetrics(cameraId) {
  return {
    waitTime: Math.floor(Math.random() * 45) + 5,
    vehicleQueue: Math.floor(Math.random() * 30) + 1,
    lightStatus: ['Green', 'Yellow', 'Red'][Math.floor(Math.random() * 3)],
    cameraId,
    fps: Math.floor(Math.random() * 10) + 25,
  }
}

const LIGHT_COLORS = { Green: 'text-success', Yellow: 'text-warning', Red: 'text-danger' }
const LIGHT_BG = { Green: 'bg-success/15', Yellow: 'bg-warning/15', Red: 'bg-danger/15' }

function MetricCard({ icon: Icon, label, value, unit, accent }) {
  return (
    <div className="glass-subtle rounded-2xl p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${accent || 'bg-accent/15 text-accent'}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-xs text-muted font-medium">{label}</p>
        <p className="text-lg font-bold text-text">{value}{unit && <span className="text-sm font-normal text-muted ml-1">{unit}</span>}</p>
      </div>
    </div>
  )
}

function QuadrantCard({ camera, metrics, simLabel, snapshotUrl }) {
  const lightColor = LIGHT_COLORS[metrics.lightStatus]
  const lightBg = LIGHT_BG[metrics.lightStatus]
  const [snapshotFailed, setSnapshotFailed] = useState(false)

  return (
    <div className="glass rounded-[var(--radius-card)] shadow-card hover:shadow-card-hover p-6 flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-text">{camera.direction}</h3>
          <p className="text-xs text-muted">{camera.name}</p>
        </div>
        <span className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${
          camera.status === 'online'
            ? 'text-success bg-success/15 border-success/20'
            : 'text-danger bg-danger/15 border-danger/20'
        }`}>
          <Circle className="w-2 h-2 fill-current" />
          {camera.status === 'online' ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>

      <div className="relative aspect-video bg-gradient-to-br from-white/5 to-white/[0.02] rounded-2xl overflow-hidden flex items-center justify-center border border-white/5">
        {snapshotUrl && !snapshotFailed ? (
          <img
            src={snapshotUrl}
            alt={`Live SUMO simulation view -- ${camera.direction} approach`}
            className="absolute inset-0 w-full h-full object-cover"
            onError={() => setSnapshotFailed(true)}
            onLoad={() => setSnapshotFailed(false)}
          />
        ) : (
          <>
            <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.02)_2px,rgba(255,255,255,0.02)_4px)]" />
            <div className="text-center z-10">
              <Activity className="w-8 h-8 text-white/15 mx-auto mb-2" />
              <p className="text-white/30 text-sm font-medium">{simLabel || 'RTSP Stream'}</p>
              <p className="text-white/20 text-xs mt-1">
                {camera.id}{metrics.fps != null ? ` · ${metrics.fps} FPS` : ''}
              </p>
            </div>
          </>
        )}
        <div className="absolute top-3 left-3 glass px-2.5 py-1 rounded-lg text-xs font-mono text-white/70">
          {camera.id}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <MetricCard icon={Clock} label="Wait Time" value={metrics.waitTime != null ? metrics.waitTime : '--'} unit={metrics.waitTime != null ? 'sec' : undefined} />
        <MetricCard icon={Car} label="Queue" value={metrics.vehicleQueue} unit="cars" />
        <MetricCard
          icon={Lightbulb}
          label="Signal"
          value={metrics.lightStatus}
          accent={`${lightBg} ${lightColor}`}
        />
      </div>
    </div>
  )
}

function useLiveJunctionState(isLive) {
  const [liveState, setLiveState] = useState({ active: false })

  useEffect(() => {
    if (!isLive) return undefined
    let cancelled = false

    const poll = async () => {
      try {
        const res = await fetch(`${PPO_API}/api/live_state`)
        const data = await res.json()
        if (!cancelled) setLiveState(data)
      } catch {
        if (!cancelled) setLiveState({ active: false })
      }
    }

    poll()
    const interval = setInterval(poll, 1000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [isLive])

  return liveState
}

function RunAgentControl({ disabled, seed, containerRef }) {
  const [scenario, setScenario] = useState('Low')
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState(null)

  const run = async () => {
    setStarting(true)
    setError(null)
    let res
    try {
      res = await fetch(`${PPO_API}/api/live_demo/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
      })
    } catch {
      // fetch() itself threw (connection refused, DNS, CORS) -- there is no
      // HTTP response at all, so this is always "backend isn't up yet",
      // never a message worth surfacing verbatim (e.g. the browser's raw
      // "Failed to fetch"). run_web.bat starts the PPO backend first but it
      // can take several seconds to import torch/sumo, so this is expected
      // right after a fresh launch -- just retry.
      setError('Still waiting for the PPO backend to finish starting (this can take up to 30 seconds after launch) -- try again in a few seconds.')
      setStarting(false)
      return
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      setError(body.detail || 'Could not start the run.')
    }
    setStarting(false)
  }

  return (
    <div className="glass-subtle rounded-2xl p-4 mb-6 flex flex-wrap items-end gap-4" ref={containerRef}>
      <div>
        <label className="text-xs text-muted font-medium block mb-1">Scenario</label>
        <div className="flex gap-1">
          {['Low', 'Medium', 'High'].map(s => (
            <button
              key={s}
              type="button"
              onClick={() => setScenario(s)}
              disabled={disabled}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                scenario === s ? 'bg-accent text-white' : 'glass-subtle text-muted'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
      <button
        type="button"
        onClick={run}
        disabled={disabled || starting}
        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Play className="w-4 h-4" />
        {starting ? 'Starting...' : disabled ? 'Running...' : 'Run Agent'}
      </button>
      {disabled && seed != null && (
        <p className="text-xs text-muted">Seed {seed} (chosen randomly)</p>
      )}
      {error && <p className="text-danger text-sm">{error}</p>}
    </div>
  )
}

export default function Dashboard() {
  const { activeJunction } = useJunction()
  const cameras = activeJunction?.cameras || []
  const isLive = activeJunction?.id === LIVE_JUNCTION_ID
  const runControlRef = useRef(null)
  const gridRef = useRef(null)

  const [metrics, setMetrics] = useState(() =>
    Object.fromEntries(cameras.map(c => [c.id, generateMetrics(c.id)]))
  )

  useEffect(() => {
    if (isLive) return undefined
    setMetrics(Object.fromEntries(cameras.map(c => [c.id, generateMetrics(c.id)])))
    const interval = setInterval(() => {
      setMetrics(Object.fromEntries(cameras.map(c => [c.id, generateMetrics(c.id)])))
    }, 5000)
    return () => clearInterval(interval)
  }, [activeJunction?.id, isLive])

  const liveState = useLiveJunctionState(isLive)

  const liveMetricsFor = (camera) => {
    const dir = camera.direction.toLowerCase()
    return {
      waitTime: null,
      vehicleQueue: liveState.lane_queues?.[dir] ?? 0,
      lightStatus: liveState.phase_colors?.[dir] || 'Red',
      cameraId: camera.id,
      fps: null,
    }
  }

  // Cache-busted on every step published by the running episode, so the
  // <img> actually refreshes instead of showing a browser-cached frame.
  const snapshotUrl = isLive && liveState.active
    ? `${PPO_API}/static/live_snapshot.png?step=${liveState.step ?? 0}`
    : null

  const gridCols = cameras.length <= 2
    ? 'grid-cols-1 lg:grid-cols-2'
    : cameras.length <= 4
      ? 'grid-cols-1 lg:grid-cols-2'
      : 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3'

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text">Dashboard</h1>
        <p className="text-muted mt-1">
          {activeJunction?.name} — {cameras.length} camera{cameras.length !== 1 ? 's' : ''} across {activeJunction?.directions.length} direction{activeJunction?.directions.length !== 1 ? 's' : ''}
        </p>
      </div>

      {isLive && <RunAgentControl disabled={liveState.active} seed={liveState.seed} containerRef={runControlRef} />}

      {isLive && !liveState.active && (
        <div className="glass rounded-2xl p-8 text-center text-muted mb-6">
          No simulation running. Pick a scenario above, then Run Agent to watch
          the trained PPO agent control this junction live (a random seed is
          chosen for you each time).
        </div>
      )}

      <div className={`grid ${gridCols} gap-6`} ref={gridRef}>
        {cameras.map(camera => (
          <QuadrantCard
            key={camera.id}
            camera={camera}
            metrics={isLive ? liveMetricsFor(camera) : (metrics[camera.id] || generateMetrics(camera.id))}
            simLabel={isLive ? 'SUMO Simulation' : null}
            snapshotUrl={snapshotUrl}
          />
        ))}
      </div>

      <Tour
        steps={
          isLive
            ? [
                {
                  target: runControlRef,
                  title: 'Run the agent live',
                  text: 'Pick a traffic scenario and click Run Agent. A random seed is chosen for you -- this launches a real SUMO episode controlled by the trained PPO agent, not a scripted demo.',
                },
                {
                  target: gridRef,
                  title: 'Watch it work',
                  text: 'These four cards mirror the real intersection: live vehicle queue counts and signal color per direction, plus a live snapshot of the actual simulation once a run is active.',
                },
              ]
            : [
                {
                  target: gridRef,
                  title: 'Camera grid',
                  text: 'This dashboard shows simulated demo data for this junction. Only "Live Junction (SUMO Simulation)" is backed by the real trained PPO agent -- switch to it from the sidebar to run a genuine live episode.',
                },
              ]
        }
      />
    </div>
  )
}
