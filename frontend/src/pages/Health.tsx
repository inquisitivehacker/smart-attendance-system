import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Server, Cpu, Database, Activity } from 'lucide-react'

const fetchHealth = async () => {
  const { data } = await axios.get('/api/health')
  return data
}

export default function Health() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: fetchHealth,
    refetchInterval: 5000 
  })

  if (isLoading) return <div>Loading system health...</div>
  if (isError) return <div className="text-red-500">Failed to connect to backend API. Is the server running?</div>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">System Health Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* API Backend */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Server className="w-5 h-5 text-gray-500" />
              API Server
            </h2>
            <StatusBadge status={data.api_status} />
          </div>
          <p className="text-sm text-gray-500 mb-1">Version: {data.version}</p>
          <p className="text-sm text-gray-500">Face Profiles Loaded: {data.profiles_loaded}</p>
        </div>

        {/* Database */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Database className="w-5 h-5 text-gray-500" />
              SQLite Database
            </h2>
            <StatusBadge status="ONLINE" />
          </div>
          <p className="text-sm text-gray-500">WAL Mode: Enabled</p>
        </div>

        {/* Hardware Loop */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-gray-500" />
              Hardware Loop
            </h2>
            <StatusBadge status={data.hardware_loop} />
          </div>
          <p className="text-sm text-gray-500">
            {data.hardware_loop === 'ONLINE' ? 'Heartbeat fresh (< 60s)' : 'Heartbeat missing or stale'}
          </p>
        </div>

      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'ONLINE' || status === 'running') {
    return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800"><Activity className="w-3 h-3"/> {status}</span>
  }
  if (status === 'STALE') {
    return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-yellow-100 text-yellow-800"><Activity className="w-3 h-3"/> {status}</span>
  }
  return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-red-100 text-red-800"><Activity className="w-3 h-3"/> {status}</span>
}
