import { useState } from 'react'
import { X, Eye, EyeOff, KeyRound } from 'lucide-react'

export default function ProfileModal({ user, groups = [], onClose, onSave, isAdmin, isSelf }) {
  const [name, setName] = useState(user.name)
  const [username, setUsername] = useState(user.username || '')
  const [email, setEmail] = useState(user.email || '')
  const [employeeId, setEmployeeId] = useState(user.employeeId || '')
  const [role, setRole] = useState(user.role)
  const [status, setStatus] = useState(user.status || 'Active')
  const [newPassword, setNewPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [userGroups, setUserGroups] = useState(user.groups || [])

  const toggleGroup = (gid) => setUserGroups(prev => prev.includes(gid) ? prev.filter(g => g !== gid) : [...prev, gid])

  const handleSave = () => {
    onSave({
      ...user,
      name, username, email, employeeId, role, status,
      avatar: name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase(),
      groups: userGroups,
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-[60] p-4" onClick={onClose}>
      <div className="glass-strong rounded-[var(--radius-card)] shadow-card-hover w-full max-w-lg p-8 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-11 h-11 rounded-full flex items-center justify-center text-white text-sm font-semibold ${
              user.role === 'Administrator' ? 'bg-gradient-to-br from-accent to-violet-500' : 'bg-gradient-to-br from-cyan-500 to-sky-400'
            }`}>
              {user.avatar}
            </div>
            <div>
              <p className="font-semibold text-text">{isSelf ? 'My Profile' : 'Edit User'}</p>
              <p className="text-xs text-muted">@{user.username}{user.employeeId ? ` · ${user.employeeId}` : ''}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-text cursor-pointer"><X className="w-5 h-5" /></button>
        </div>

        <div className="space-y-4">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider">Personal Info</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">Full Name</label>
              <input value={name} onChange={e => setName(e.target.value)} className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">Employee ID</label>
              <input value={employeeId} onChange={e => setEmployeeId(e.target.value)} disabled={!isAdmin} className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none disabled:opacity-50" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">Email</label>
            <input value={email} onChange={e => setEmail(e.target.value)} type="email" className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none" />
          </div>

          <div className="pt-2 border-t border-border">
            <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">Login Credentials</p>
            <div className="glass-subtle rounded-2xl p-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">Username (used to sign in)</label>
                <input value={username} onChange={e => setUsername(e.target.value)} disabled={!isAdmin && !isSelf} placeholder="e.g., jsmith" className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none disabled:opacity-50" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                  <span className="flex items-center gap-1.5"><KeyRound className="w-3 h-3" />New Password</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder={isSelf ? 'Enter new password' : 'Set new password for user'}
                    className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text placeholder:text-muted/50 focus:outline-none pr-10"
                  />
                  <button onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text cursor-pointer">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[10px] text-muted mt-1.5">Leave blank to keep current password</p>
              </div>
            </div>
          </div>

          {isAdmin && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">Role</label>
                <select value={role} onChange={e => setRole(e.target.value)} className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none">
                  <option>Administrator</option>
                  <option>Operator</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">Status</label>
                <select value={status} onChange={e => setStatus(e.target.value)} className="w-full px-4 py-2.5 rounded-2xl glass-input text-sm text-text focus:outline-none">
                  <option>Active</option>
                  <option>Inactive</option>
                </select>
              </div>
            </div>
          )}

          {isAdmin && groups.length > 0 && (
            <div>
              <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-2">Groups</label>
              <div className="flex flex-wrap gap-2">
                {groups.map(g => (
                  <button
                    key={g.id}
                    onClick={() => toggleGroup(g.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition-all border ${
                      userGroups.includes(g.id)
                        ? 'text-white shadow-md'
                        : 'glass-subtle text-muted hover:text-text'
                    }`}
                    style={userGroups.includes(g.id) ? { backgroundColor: g.color, borderColor: g.color } : {}}
                  >
                    {g.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="flex-1 py-3 glass text-text font-semibold rounded-2xl hover:bg-accent/10 cursor-pointer text-sm">Cancel</button>
          <button onClick={handleSave} className="flex-1 py-3 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl cursor-pointer text-sm shadow-lg shadow-accent/25">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}
