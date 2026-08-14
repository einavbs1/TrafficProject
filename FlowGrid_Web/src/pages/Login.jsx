import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { useJunction } from '../JunctionContext'
import { Eye, EyeOff } from 'lucide-react'
import BackgroundDecor from '../components/BackgroundDecor'
import ThemeToggle from '../components/ThemeToggle'

export default function Login() {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const { clearJunction } = useJunction()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    await new Promise(r => setTimeout(r, 600))
    const success = login(username, password)
    if (success) {
      clearJunction()
      navigate('/')
    } else {
      setError('Invalid credentials. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-6 relative overflow-hidden">
      <BackgroundDecor />

      <div className="absolute top-6 right-6 z-20">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="glass-strong rounded-[var(--radius-card)] p-10 shadow-card">
          <div className="flex items-center justify-center gap-3 mb-2">
            <svg width="44" height="44" viewBox="0 0 44 44" fill="none">
              <rect x="2" y="2" width="40" height="40" rx="12" fill="url(#loginGrad)" />
              <path d="M22 10v24M14 18h16M14 26h16" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="22" cy="14" r="2.5" fill="#34d399" />
              <circle cx="22" cy="22" r="2.5" fill="#fbbf24" />
              <circle cx="22" cy="30" r="2.5" fill="#f87171" />
              <defs>
                <linearGradient id="loginGrad" x1="0" y1="0" x2="44" y2="44">
                  <stop stopColor="#7c5cfc" />
                  <stop offset="1" stopColor="#ec4899" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-text text-center mt-5">Welcome back</h1>
          <p className="text-muted text-center mt-2 mb-8 text-sm">Sign in to your FlowGrid account</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-text mb-2">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter your username"
                className="w-full px-4 py-3.5 rounded-2xl glass-input text-text placeholder:text-muted/50 focus:outline-none text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-4 py-3.5 rounded-2xl glass-input text-text placeholder:text-muted/50 focus:outline-none text-sm pr-11"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded border-border text-accent focus:ring-accent/30 bg-transparent" />
                <span className="text-sm text-muted">Remember me</span>
              </label>
              <button type="button" className="text-sm text-accent hover:text-accent-hover font-medium cursor-pointer">
                Forgot password?
              </button>
            </div>

            {error && (
              <div className="bg-danger/15 text-danger text-sm px-4 py-3 rounded-2xl border border-danger/20">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-gradient-to-r from-accent to-pink-500 hover:from-accent-hover hover:to-pink-600 text-white font-semibold rounded-2xl disabled:opacity-60 cursor-pointer text-sm shadow-lg shadow-accent/25 hover:shadow-accent/40"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-muted/50 mt-6">
          Demo credentials — admin / admin123 &nbsp;or&nbsp; operator / op123
        </p>
      </div>
    </div>
  )
}
