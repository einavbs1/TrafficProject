import { useState } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { useJunction } from '../JunctionContext'
import ProfileModal from './ProfileModal'
import {
  LayoutDashboard,
  Video,
  Settings,
  Users,
  BarChart3,
  GitBranch,
  LogOut,
  ArrowLeftRight,
  UserPen,
  MapPin,
  Lock,
  X,
} from 'lucide-react'
import ThemeToggle from './ThemeToggle'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', needsJunction: true },
  { to: '/live-stream', icon: Video, label: 'Live Stream', needsJunction: true },
  { to: '/devices', icon: Settings, label: 'Device Settings', needsJunction: true },
  { to: '/users', icon: Users, label: 'Manage Users' },
  { to: '/reports', icon: BarChart3, label: 'Reports' },
  { to: '/junctions', icon: GitBranch, label: 'Junctions' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const { activeJunction, clearJunction, hasSelectedJunction } = useJunction()
  const navigate = useNavigate()
  const location = useLocation()
  const [showProfile, setShowProfile] = useState(false)

  const handleLogout = () => {
    clearJunction()
    logout()
    navigate('/login')
  }

  const handleSwitch = () => {
    navigate('/select-junction')
  }

  const handleClear = () => {
    clearJunction()
    navigate('/select-junction')
  }

  const handleProfileSave = (updated) => {
    setShowProfile(false)
  }

  const isOnJunctionSelect = location.pathname === '/select-junction'

  return (
    <>
    <aside className="fixed left-0 top-0 bottom-0 w-72 glass-strong flex flex-col z-50 m-0">
      <div className="p-7 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" className="shrink-0">
            <rect width="40" height="40" rx="12" fill="url(#sidebarGrad)" />
            <path d="M20 9v22M13 16h14M13 24h14" stroke="white" strokeWidth="2.2" strokeLinecap="round" />
            <circle cx="20" cy="12.5" r="2" fill="#34d399" />
            <circle cx="20" cy="20" r="2" fill="#fbbf24" />
            <circle cx="20" cy="27.5" r="2" fill="#f87171" />
            <defs>
              <linearGradient id="sidebarGrad" x1="0" y1="0" x2="40" y2="40">
                <stop stopColor="#7c5cfc" />
                <stop offset="1" stopColor="#ec4899" />
              </linearGradient>
            </defs>
          </svg>
          <span className="text-xl font-bold text-text tracking-tight">FlowGrid</span>
        </div>
        <ThemeToggle />
      </div>

      {activeJunction ? (
        <div className="mx-4 mb-3 p-3 rounded-2xl glass-subtle">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <p className="text-xs text-muted font-medium uppercase tracking-wider">Active Junction</p>
              <p className="text-sm font-semibold text-text truncate mt-0.5">{activeJunction.name}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={handleSwitch}
                className="p-2 rounded-xl hover:bg-accent/10 text-muted hover:text-accent cursor-pointer"
                title="Switch junction"
              >
                <ArrowLeftRight className="w-4 h-4" />
              </button>
              <button
                onClick={handleClear}
                className="p-2 rounded-xl hover:bg-danger/10 text-muted hover:text-danger cursor-pointer"
                title="Clear junction"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          onClick={() => navigate('/select-junction')}
          className={`mx-4 mb-3 p-3 rounded-2xl border-2 border-dashed cursor-pointer transition-all text-left ${
            isOnJunctionSelect
              ? 'border-accent/30 bg-accent/5'
              : 'border-border hover:border-accent/30 hover:bg-accent/5'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <MapPin className="w-4 h-4 text-warning shrink-0" />
            <div>
              <p className="text-xs font-semibold text-warning">No Junction Selected</p>
              <p className="text-[11px] text-muted mt-0.5">Click to select a junction</p>
            </div>
          </div>
        </button>
      )}

      <nav className="flex-1 px-4 mt-1 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, label, needsJunction }) => {
          const disabled = needsJunction && !hasSelectedJunction
          if (disabled) {
            return (
              <div
                key={to}
                className="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium text-muted/40 cursor-not-allowed select-none"
                title="Select a junction first"
              >
                <Icon className="w-5 h-5" />
                {label}
                <Lock className="w-3 h-3 ml-auto" />
              </div>
            )
          }
          return (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'glass-strong text-accent shadow-lg shadow-accent/10'
                    : 'text-muted hover:text-text hover:bg-accent/5'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              {label}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-5 mx-4 mb-4 rounded-2xl glass-subtle">
        <button
          onClick={() => setShowProfile(true)}
          className="flex items-center gap-3 w-full text-left cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent to-pink-500 flex items-center justify-center text-white text-sm font-semibold shadow-lg shadow-accent/20 group-hover:shadow-accent/40 transition-shadow">
            {user?.avatar}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-text truncate group-hover:text-accent transition-colors">{user?.name}</p>
            <p className="text-xs text-muted">{user?.role}</p>
          </div>
          <UserPen className="w-4 h-4 text-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
        </button>
        <button
          onClick={handleLogout}
          className="mt-3 flex items-center gap-2 text-sm text-muted hover:text-danger w-full px-1 cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>

    {showProfile && user && (
      <ProfileModal
        user={{
          ...user,
          email: user.email || `${user.username}@flowgrid.io`,
          employeeId: user.employeeId || 'EMP-001',
          status: 'Active',
        }}
        onClose={() => setShowProfile(false)}
        onSave={handleProfileSave}
        isAdmin={user.role === 'Administrator'}
        isSelf={true}
      />
    )}
    </>
  )
}
