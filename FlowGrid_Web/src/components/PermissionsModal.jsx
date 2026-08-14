import { useState } from 'react'
import { X } from 'lucide-react'
import Toggle from './Toggle'

const PERMISSIONS = ['View Dashboard', 'Manage Cameras', 'Edit Junctions', 'View Reports', 'Manage Users', 'System Settings']

export default function PermissionsModal({ user, onClose }) {
  const [perms, setPerms] = useState(() =>
    Object.fromEntries(PERMISSIONS.map((p, i) => [p, user.role === 'Administrator' || i < 4]))
  )
  const toggle = (perm) => setPerms(prev => ({ ...prev, [perm]: !prev[perm] }))

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="glass-strong rounded-[var(--radius-card)] shadow-card-hover w-full max-w-md p-8" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-semibold ${
              user.role === 'Administrator' ? 'bg-gradient-to-br from-accent to-violet-500' : 'bg-gradient-to-br from-cyan-500 to-sky-400'
            }`}>{user.avatar}</div>
            <div>
              <p className="font-semibold text-text">{user.name}</p>
              <p className="text-xs text-muted">{user.role}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-text cursor-pointer"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-3">
          {PERMISSIONS.map(perm => (
            <div key={perm} className="flex items-center justify-between py-2.5">
              <span className="text-sm text-text">{perm}</span>
              <Toggle value={perms[perm]} onChange={() => toggle(perm)} />
            </div>
          ))}
        </div>
        <button onClick={onClose} className="mt-6 w-full py-3 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl cursor-pointer text-sm shadow-lg shadow-accent/25">
          Save Permissions
        </button>
      </div>
    </div>
  )
}
