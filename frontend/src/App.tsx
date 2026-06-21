import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Radio, Users, Calendar, BarChart2, Shield, Settings } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Pages (to be implemented)
import Dashboard from './pages/Dashboard'
import LiveMonitor from './pages/LiveMonitor'
import Sessions from './pages/Sessions'
import Students from './pages/Students'
import Enrollment from './pages/Enrollment'
import Reports from './pages/Reports'
import Analytics from './pages/Analytics'
import Health from './pages/Health'

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs))
}

function Sidebar() {
  const location = useLocation()
  
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Live Monitor', path: '/live', icon: Radio },
    { name: 'Sessions', path: '/sessions', icon: Calendar },
    { name: 'Students', path: '/students', icon: Users },
    { name: 'Reports', path: '/reports', icon: BarChart2 },
    { name: 'Face Enrollment', path: '/enrollment', icon: Shield },
    { name: 'Analytics', path: '/analytics', icon: BarChart2 },
    { name: 'System Health', path: '/health', icon: Settings },
  ]

  return (
    <div className="w-64 bg-white border-r min-h-screen flex flex-col">
      <div className="p-4 border-b">
        <h1 className="text-xl font-bold text-gray-800">Smart Attendance</h1>
        <p className="text-xs text-gray-500 mt-1">Faculty Dashboard</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive 
                  ? "bg-blue-50 text-blue-700" 
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <Icon className="w-5 h-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 p-8 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/live" element={<LiveMonitor />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/students" element={<Students />} />
            <Route path="/enrollment" element={<Enrollment />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/health" element={<Health />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
