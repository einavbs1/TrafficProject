import { useState } from 'react'
import { useAuth } from '../AuthContext'
import ProfileModal from '../components/ProfileModal'
import StatusPill from '../components/StatusPill'
import PermissionsModal from '../components/PermissionsModal'
import CreateGroupModal from '../components/CreateGroupModal'
import {
  Search, ChevronLeft, ChevronRight, Shield, UserPen, Plus,
  UsersRound, Tag, Trash2,
} from 'lucide-react'

const INITIAL_GROUPS = [
  { id: 1, name: 'Traffic Ops', color: '#7c5cfc' },
  { id: 2, name: 'Field Technicians', color: '#ec4899' },
  { id: 3, name: 'Supervisors', color: '#f59e0b' },
]

const INITIAL_USERS = [
  { id: 1, name: 'Alex Morgan', email: 'alex.morgan@flowgrid.io', role: 'Administrator', status: 'Active', avatar: 'AM', username: 'admin', employeeId: 'EMP-001', groups: [1, 3] },
  { id: 2, name: 'Jordan Lee', email: 'jordan.lee@flowgrid.io', role: 'Operator', status: 'Active', avatar: 'JL', username: 'operator', employeeId: 'EMP-002', groups: [1] },
  { id: 3, name: 'Sam Patel', email: 'sam.patel@flowgrid.io', role: 'Operator', status: 'Active', avatar: 'SP', username: 'spatel', employeeId: 'EMP-003', groups: [2] },
  { id: 4, name: 'Casey Davis', email: 'casey.davis@flowgrid.io', role: 'Administrator', status: 'Inactive', avatar: 'CD', username: 'cdavis', employeeId: 'EMP-004', groups: [3] },
  { id: 5, name: 'Riley Chen', email: 'riley.chen@flowgrid.io', role: 'Operator', status: 'Active', avatar: 'RC', username: 'rchen', employeeId: 'EMP-005', groups: [1, 2] },
  { id: 6, name: 'Taylor Kim', email: 'taylor.kim@flowgrid.io', role: 'Operator', status: 'Active', avatar: 'TK', username: 'tkim', employeeId: 'EMP-006', groups: [2] },
  { id: 7, name: 'Morgan Blake', email: 'morgan.blake@flowgrid.io', role: 'Operator', status: 'Inactive', avatar: 'MB', username: 'mblake', employeeId: 'EMP-007', groups: [] },
  { id: 8, name: 'Drew Wilson', email: 'drew.wilson@flowgrid.io', role: 'Administrator', status: 'Active', avatar: 'DW', username: 'dwilson', employeeId: 'EMP-008', groups: [1, 3] },
]

export default function Users() {
  const { user: currentUser } = useAuth()
  const isAdmin = currentUser?.role === 'Administrator'

  const [users, setUsers] = useState(INITIAL_USERS)
  const [groups, setGroups] = useState(INITIAL_GROUPS)
  const [search, setSearch] = useState('')
  const [filterGroup, setFilterGroup] = useState(null)
  const [filterRole, setFilterRole] = useState(null)
  const [page, setPage] = useState(1)
  const [editUser, setEditUser] = useState(null)
  const [permUser, setPermUser] = useState(null)
  const [showCreateGroup, setShowCreateGroup] = useState(false)
  const perPage = 6

  const filtered = users.filter(u => {
    const matchSearch = u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      u.employeeId.toLowerCase().includes(search.toLowerCase())
    const matchGroup = !filterGroup || u.groups.includes(filterGroup)
    const matchRole = !filterRole || u.role === filterRole
    return matchSearch && matchGroup && matchRole
  })
  const totalPages = Math.ceil(filtered.length / perPage)
  const paginated = filtered.slice((page - 1) * perPage, page * perPage)

  const handleSaveUser = (updated) => {
    setUsers(prev => prev.map(u => u.id === updated.id ? updated : u))
  }

  const handleCreateGroup = (group) => {
    setGroups(prev => [...prev, { ...group, id: Math.max(...prev.map(g => g.id), 0) + 1 }])
  }

  const handleDeleteGroup = (gid) => {
    setGroups(prev => prev.filter(g => g.id !== gid))
    setUsers(prev => prev.map(u => ({ ...u, groups: u.groups.filter(g => g !== gid) })))
    if (filterGroup === gid) setFilterGroup(null)
  }

  const isSelf = (u) => u.username === currentUser?.username

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text">Manage Users</h1>
          <p className="text-muted mt-1">User profiles, groups, and permissions</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setEditUser({
              id: Math.max(...users.map(u => u.id), 0) + 1,
              name: '', email: '', role: 'Operator', status: 'Active',
              avatar: '', username: '', employeeId: `EMP-${String(users.length + 1).padStart(3, '0')}`,
              groups: [], _isNew: true,
            })}
            className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl cursor-pointer text-sm shadow-lg shadow-accent/25"
          >
            <Plus className="w-4 h-4" />
            Add User
          </button>
        )}
      </div>

      <div className="mb-6">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider flex items-center gap-1.5">
            <UsersRound className="w-3.5 h-3.5" />Groups
          </p>
          {groups.map(g => (
            <div key={g.id} className="flex items-center gap-0.5">
              <button
                onClick={() => setFilterGroup(filterGroup === g.id ? null : g.id)}
                className={`px-3 py-1.5 rounded-l-xl text-xs font-semibold cursor-pointer transition-all border ${
                  filterGroup === g.id ? 'text-white shadow-md' : 'glass-subtle text-muted hover:text-text'
                }`}
                style={filterGroup === g.id ? { backgroundColor: g.color, borderColor: g.color } : {}}
              >
                <span className="flex items-center gap-1.5">
                  <Tag className="w-3 h-3" />
                  {g.name}
                  <span className="opacity-70">({users.filter(u => u.groups.includes(g.id)).length})</span>
                </span>
              </button>
              {isAdmin && (
                <button
                  onClick={() => handleDeleteGroup(g.id)}
                  className="px-1.5 py-1.5 rounded-r-xl text-xs glass-subtle text-muted hover:text-danger cursor-pointer border border-l-0 border-border"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}
          {isAdmin && (
            <button
              onClick={() => setShowCreateGroup(true)}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold glass-subtle text-muted hover:text-text cursor-pointer border border-dashed border-border hover:border-accent/30"
            >
              <Plus className="w-3 h-3 inline mr-1" />New Group
            </button>
          )}
          <div className="w-px h-5 bg-border mx-1" />
          {['Administrator', 'Operator'].map(r => (
            <button
              key={r}
              onClick={() => setFilterRole(filterRole === r ? null : r)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition-all border ${
                filterRole === r
                  ? r === 'Administrator' ? 'bg-accent/20 text-accent border-accent/30' : 'bg-cyan-500/20 text-cyan-500 border-cyan-500/30'
                  : 'glass-subtle text-muted hover:text-text'
              }`}
            >
              {r}s
            </button>
          ))}
        </div>
      </div>

      <div className="glass rounded-[var(--radius-card)] shadow-card">
        <div className="p-6 border-b border-border">
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              type="text"
              placeholder="Search by name, email, or ID..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              className="w-full pl-10 pr-4 py-2.5 rounded-2xl glass-input text-sm text-text placeholder:text-muted/50 focus:outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left text-xs font-semibold text-muted uppercase tracking-wider px-6 py-4">User</th>
                <th className="text-left text-xs font-semibold text-muted uppercase tracking-wider px-6 py-4">Role</th>
                <th className="text-left text-xs font-semibold text-muted uppercase tracking-wider px-6 py-4">Groups</th>
                <th className="text-left text-xs font-semibold text-muted uppercase tracking-wider px-6 py-4">Status</th>
                <th className="text-right text-xs font-semibold text-muted uppercase tracking-wider px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginated.map(u => (
                <tr key={u.id} className="border-b border-border hover:bg-accent/[0.04]">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold ${
                        u.role === 'Administrator'
                          ? 'bg-gradient-to-br from-accent/30 to-violet-500/30 text-accent'
                          : 'bg-gradient-to-br from-cyan-500/25 to-sky-400/25 text-cyan-500'
                      }`}>{u.avatar}</div>
                      <div>
                        <span className="text-sm font-semibold text-text block">
                          {u.name}
                          {isSelf(u) && <span className="text-xs text-accent ml-1.5">(You)</span>}
                        </span>
                        <span className="text-xs text-muted">@{u.username} · {u.email}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                      u.role === 'Administrator' ? 'bg-accent/15 text-accent border-accent/20' : 'bg-cyan-500/15 text-cyan-500 border-cyan-500/20'
                    }`}>
                      {u.role === 'Administrator' ? '⬥' : '◆'} {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {u.groups.map(gid => {
                        const g = groups.find(gr => gr.id === gid)
                        if (!g) return null
                        return (
                          <span key={gid} className="px-2 py-0.5 rounded-md text-[10px] font-semibold text-white" style={{ backgroundColor: g.color }}>
                            {g.name}
                          </span>
                        )
                      })}
                      {u.groups.length === 0 && <span className="text-xs text-muted/50">—</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4"><StatusPill status={u.status} /></td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {(isAdmin || isSelf(u)) && (
                        <button
                          onClick={() => setEditUser(u)}
                          className="inline-flex items-center gap-1.5 px-3 py-2 glass-subtle text-text rounded-xl text-xs font-medium hover:bg-accent/10 cursor-pointer"
                        >
                          <UserPen className="w-3.5 h-3.5" />
                          {isSelf(u) ? 'My Profile' : 'Edit'}
                        </button>
                      )}
                      {isAdmin && (
                        <button
                          onClick={() => setPermUser(u)}
                          className="inline-flex items-center gap-1.5 px-3 py-2 bg-accent/15 text-accent rounded-xl text-xs font-medium hover:bg-accent/25 cursor-pointer border border-accent/20"
                        >
                          <Shield className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-border">
          <p className="text-sm text-muted">
            Showing {Math.min((page - 1) * perPage + 1, filtered.length)}–{Math.min(page * perPage, filtered.length)} of {filtered.length}
          </p>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="p-2 rounded-xl hover:bg-accent/5 disabled:opacity-30 cursor-pointer text-muted">
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} onClick={() => setPage(i + 1)} className={`w-9 h-9 rounded-xl text-sm font-medium cursor-pointer ${
                page === i + 1 ? 'bg-gradient-to-r from-accent to-pink-500 text-white shadow-lg shadow-accent/20' : 'hover:bg-accent/5 text-muted'
              }`}>{i + 1}</button>
            ))}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages || totalPages === 0} className="p-2 rounded-xl hover:bg-accent/5 disabled:opacity-30 cursor-pointer text-muted">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {editUser && (
        <ProfileModal
          user={editUser}
          groups={groups}
          onClose={() => setEditUser(null)}
          onSave={(updated) => {
            if (updated._isNew) {
              const { _isNew, ...clean } = updated
              setUsers(prev => [...prev, clean])
            } else {
              handleSaveUser(updated)
            }
          }}
          isAdmin={isAdmin}
          isSelf={isSelf(editUser)}
        />
      )}
      {permUser && <PermissionsModal user={permUser} onClose={() => setPermUser(null)} />}
      {showCreateGroup && <CreateGroupModal onClose={() => setShowCreateGroup(false)} onCreate={handleCreateGroup} />}
    </div>
  )
}
