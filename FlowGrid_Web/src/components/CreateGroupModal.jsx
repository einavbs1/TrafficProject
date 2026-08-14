import { useState } from 'react'
import { X } from 'lucide-react'

const COLORS = ['#7c5cfc', '#ec4899', '#f59e0b', '#34d399', '#f87171', '#06b6d4', '#8b5cf6', '#64748b']

export default function CreateGroupModal({ onClose, onCreate }) {
  const [name, setName] = useState('')
  const [color, setColor] = useState('#7c5cfc')

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="glass-strong rounded-[var(--radius-card)] shadow-card-hover w-full max-w-sm p-8" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-text">Create Group</h2>
          <button onClick={onClose} className="text-muted hover:text-text cursor-pointer"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">Group Name</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., Night Shift" className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-2">Color</label>
            <div className="flex gap-2">
              {COLORS.map(c => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={`w-8 h-8 rounded-xl cursor-pointer transition-transform ${color === c ? 'scale-110 ring-2 ring-white/50' : 'hover:scale-105'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-3 glass text-text font-semibold rounded-2xl hover:bg-accent/10 cursor-pointer text-sm">Cancel</button>
          <button
            onClick={() => { if (name.trim()) { onCreate({ name: name.trim(), color }); onClose() } }}
            disabled={!name.trim()}
            className="flex-1 py-3 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl cursor-pointer text-sm shadow-lg shadow-accent/25 disabled:opacity-40"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  )
}
