import { useState } from 'react'
import { Activity, Circle, Maximize2, Volume2, Settings } from 'lucide-react'
import { useJunction } from '../JunctionContext'

function StreamCard({ camera, isSelected, onSelect }) {
  const isOnline = camera.status === 'online'
  return (
    <button
      onClick={() => onSelect(camera.id)}
      className={`w-full text-left p-4 rounded-2xl border transition-all cursor-pointer ${
        isSelected
          ? 'glass-strong border-accent/30 shadow-lg shadow-accent/10'
          : 'border-transparent hover:bg-accent/5'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-text">{camera.id}</span>
        <span className={`flex items-center gap-1 text-xs font-semibold ${isOnline ? 'text-success' : 'text-muted'}`}>
          <Circle className={`w-2 h-2 ${isOnline ? 'fill-success' : 'fill-muted'}`} />
          {isOnline ? 'Live' : 'Offline'}
        </span>
      </div>
      <p className="text-sm text-text">{camera.name}</p>
      <p className="text-xs text-muted mt-1">{camera.direction} direction</p>
    </button>
  )
}

export default function LiveStream() {
  const { activeJunction } = useJunction()
  const cameras = activeJunction?.cameras || []
  const [selected, setSelected] = useState(cameras[0]?.id)
  const activeCamera = cameras.find(c => c.id === selected) || cameras[0]

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text">Live Stream</h1>
        <p className="text-muted mt-1">{activeJunction?.name} — {cameras.length} camera feed{cameras.length !== 1 ? 's' : ''}</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <div className="xl:col-span-3">
          <div className="glass rounded-[var(--radius-card)] shadow-card overflow-hidden">
            <div className="relative aspect-video bg-gradient-to-br from-white/5 to-white/[0.02] flex items-center justify-center">
              <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.02)_2px,rgba(255,255,255,0.02)_4px)]" />
              <div className="text-center z-10">
                <Activity className="w-12 h-12 text-white/15 mx-auto mb-3" />
                <p className="text-white/30 text-lg font-medium">RTSP Stream — {activeCamera?.name}</p>
                <p className="text-white/20 text-sm mt-1">{activeCamera?.id} · {activeCamera?.direction}</p>
              </div>
              <div className="absolute top-4 left-4 flex items-center gap-2">
                <span className={`flex items-center gap-1.5 text-xs font-semibold text-white px-3 py-1.5 rounded-lg border ${
                  activeCamera?.status === 'online'
                    ? 'bg-success/70 border-success/30'
                    : 'bg-danger/70 border-danger/30'
                }`}>
                  <Circle className="w-2 h-2 fill-current" />
                  {activeCamera?.status === 'online' ? 'LIVE' : 'OFFLINE'}
                </span>
                <span className="glass text-white/70 text-xs px-2.5 py-1.5 rounded-lg font-mono">
                  {activeCamera?.id}
                </span>
              </div>
              <div className="absolute bottom-4 right-4 flex items-center gap-2">
                {[Volume2, Settings, Maximize2].map((Icon, i) => (
                  <button key={i} className="glass text-white/60 p-2 rounded-lg hover:text-white hover:bg-accent/15 cursor-pointer">
                    <Icon className="w-4 h-4" />
                  </button>
                ))}
              </div>
            </div>
            <div className="p-5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-text">{activeCamera?.name}</p>
                <p className="text-sm text-muted mt-0.5">{activeCamera?.direction} — {activeCamera?.ip}</p>
              </div>
              <span className="text-sm text-muted">1080p · {activeCamera?.type}</span>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-semibold text-muted uppercase tracking-wider px-1">Cameras</p>
          {cameras.map(camera => (
            <StreamCard
              key={camera.id}
              camera={camera}
              isSelected={selected === camera.id}
              onSelect={setSelected}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
