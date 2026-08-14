import { useState } from 'react'
import { Camera, Wifi, WifiOff, Settings, MapPin, X } from 'lucide-react'
import { useJunction } from '../JunctionContext'

function ConfigModal({ device, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="glass-strong rounded-[var(--radius-card)] shadow-card-hover w-full max-w-lg p-8" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-text">Device Configuration</h2>
          <button onClick={onClose} className="text-muted hover:text-text cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {[
            ['Device Name', device.name],
            ['Device ID', device.id],
            ['Direction', device.direction],
            ['IP Address', device.ip],
            ['RTSP URL', device.rtsp],
            ['Type', device.type],
            ['Firmware', device.firmware],
          ].map(([label, value]) => (
            <div key={label}>
              <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">{label}</label>
              <input
                defaultValue={value}
                className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none"
              />
            </div>
          ))}
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="flex-1 py-3 glass text-text font-semibold rounded-2xl hover:bg-accent/10 cursor-pointer text-sm">
            Cancel
          </button>
          <button onClick={onClose} className="flex-1 py-3 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl cursor-pointer text-sm shadow-lg shadow-accent/25">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Devices() {
  const { activeJunction } = useJunction()
  const [configDevice, setConfigDevice] = useState(null)
  const devices = activeJunction?.cameras || []

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text">Device Settings</h1>
        <p className="text-muted mt-1">{activeJunction?.name} — {devices.length} device{devices.length !== 1 ? 's' : ''}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {devices.map(device => {
          const isOnline = device.status === 'online'
          return (
            <div
              key={device.id}
              className="glass rounded-[var(--radius-card)] shadow-card hover:shadow-card-hover p-6 flex flex-col"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    isOnline ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'
                  }`}>
                    <Camera className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="font-semibold text-text text-sm">{device.id}</p>
                    <p className="text-xs text-muted">{device.type}</p>
                  </div>
                </div>
                <span className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${
                  isOnline
                    ? 'bg-success/15 text-success border-success/20'
                    : 'bg-danger/15 text-danger border-danger/20'
                }`}>
                  {isOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                  {isOnline ? 'Online' : 'Offline'}
                </span>
              </div>

              <h3 className="font-semibold text-text mb-1">{device.name}</h3>
              <p className="text-xs text-accent font-medium mb-3">{device.direction} direction</p>

              <div className="space-y-2 flex-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted">IP Address</span>
                  <span className="text-text font-mono text-xs">{device.ip}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted">RTSP</span>
                  <span className="text-text font-mono text-xs truncate max-w-[180px]">{device.rtsp}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted">Firmware</span>
                  <span className="text-text text-xs">{device.firmware}</span>
                </div>
              </div>

              <button
                onClick={() => setConfigDevice(device)}
                className="mt-5 w-full py-2.5 glass hover:bg-accent/10 text-text font-medium rounded-2xl flex items-center justify-center gap-2 cursor-pointer text-sm"
              >
                <Settings className="w-4 h-4" />
                Configuration
              </button>
            </div>
          )
        })}
      </div>

      {configDevice && <ConfigModal device={configDevice} onClose={() => setConfigDevice(null)} />}
    </div>
  )
}
