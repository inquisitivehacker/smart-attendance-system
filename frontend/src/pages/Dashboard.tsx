import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Users, UserCheck, UserMinus, BarChart3, ScanFace, XCircle } from 'lucide-react'

// Fetch dashboard summary
const fetchSummary = async () => {
  const { data } = await axios.get('/api/dashboard/summary')
  return data
}

export default function Dashboard() {
  // Poll every 5 seconds
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboardSummary'],
    queryFn: fetchSummary,
    refetchInterval: 5000 
  })

  if (isLoading) return <div className="text-gray-500">Loading dashboard...</div>
  if (isError) return <div className="text-red-500">Failed to load dashboard data. Is the backend running?</div>

  const { active_session, attendance_metrics, scan_metrics } = data

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>

      {/* Active Session Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Active Class Session</h2>
        {active_session.id ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Subject</p>
              <p className="font-medium">{active_session.subject}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Faculty</p>
              <p className="font-medium">{active_session.faculty}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Room</p>
              <p className="font-medium">{active_session.room}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Started At</p>
              <p className="font-medium">{new Date(active_session.start_time).toLocaleTimeString()}</p>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 italic">No active session currently running.</div>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard 
          title="Total Students" 
          value={attendance_metrics.total_students} 
          icon={Users} 
          color="blue" 
        />
        <MetricCard 
          title="Present Today" 
          value={attendance_metrics.present_students} 
          icon={UserCheck} 
          color="green" 
        />
        <MetricCard 
          title="Absent" 
          value={attendance_metrics.absent_students} 
          icon={UserMinus} 
          color="orange" 
        />
        <MetricCard 
          title="Attendance %" 
          value={`${attendance_metrics.attendance_percentage}%`} 
          icon={BarChart3} 
          color="indigo" 
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
         <MetricCard 
          title="Successful Scans (Today)" 
          value={scan_metrics.successful_scans_today} 
          icon={ScanFace} 
          color="green" 
        />
         <MetricCard 
          title="Failed Scans (Today)" 
          value={scan_metrics.failed_scans_today} 
          icon={XCircle} 
          color="red" 
        />
      </div>
    </div>
  )
}

function MetricCard({ title, value, icon: Icon, color }: { title: string, value: string | number, icon: any, color: string }) {
  const colorMap: Record<string, string> = {
    blue: "text-blue-600 bg-blue-50",
    green: "text-green-600 bg-green-50",
    orange: "text-orange-600 bg-orange-50",
    indigo: "text-indigo-600 bg-indigo-50",
    red: "text-red-600 bg-red-50",
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${colorMap[color]}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  )
}
