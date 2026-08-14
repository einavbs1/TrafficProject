import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import BackgroundDecor from './BackgroundDecor'

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-bg relative overflow-hidden">
      <BackgroundDecor />
      <Sidebar />
      <main className="flex-1 ml-72 p-10 relative z-10">
        <Outlet />
      </main>
    </div>
  )
}
