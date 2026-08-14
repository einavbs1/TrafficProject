import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import { ThemeProvider } from './ThemeContext'
import { JunctionProvider, useJunction } from './JunctionContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import JunctionSelect from './pages/JunctionSelect'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import Devices from './pages/Devices'
import Junctions from './pages/Junctions'
import Reports from './pages/Reports'
import LiveStream from './pages/LiveStream'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function RequiresJunction({ children }) {
  const { hasSelectedJunction } = useJunction()
  return hasSelectedJunction ? children : <Navigate to="/select-junction" replace />
}

function AppRoutes() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/select-junction" replace /> : <Login />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="select-junction" element={<JunctionSelect />} />
        <Route index element={<RequiresJunction><Dashboard /></RequiresJunction>} />
        <Route path="live-stream" element={<RequiresJunction><LiveStream /></RequiresJunction>} />
        <Route path="devices" element={<RequiresJunction><Devices /></RequiresJunction>} />
        <Route path="users" element={<Users />} />
        <Route path="reports" element={<Reports />} />
        <Route path="junctions" element={<Junctions />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <JunctionProvider>
          <AppRoutes />
        </JunctionProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
