import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

const DEMO_USERS = [
  { username: 'admin', password: 'admin123', name: 'Alex Morgan', role: 'Administrator', avatar: 'AM' },
  { username: 'operator', password: 'op123', name: 'Jordan Lee', role: 'Operator', avatar: 'JL' },
]

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = sessionStorage.getItem('fg_user')
    return saved ? JSON.parse(saved) : null
  })

  const login = useCallback((username, password) => {
    const found = DEMO_USERS.find(u => u.username === username && u.password === password)
    if (!found) return false
    const userData = { name: found.name, role: found.role, avatar: found.avatar, username: found.username }
    setUser(userData)
    sessionStorage.setItem('fg_user', JSON.stringify(userData))
    return true
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    sessionStorage.removeItem('fg_user')
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
