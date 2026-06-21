import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Target, Zap } from 'lucide-react'

const fetchAnalytics = async () => {
  const { data } = await axios.get('/api/reports/analytics')
  return data
}

export default function Analytics() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics'],
    queryFn: fetchAnalytics,
    refetchInterval: 10000 
  })

  if (isLoading) return <div>Loading analytics...</div>
  if (isError) return <div className="text-red-500">Failed to load analytics data.</div>

  const { attendance_metrics, recognition_metrics, performance_metrics } = data

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">System Analytics</h1>

      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-gray-500" />
          Recognition Performance
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col items-center justify-center">
            <p className="text-sm font-medium text-gray-500 mb-2">Success Rate</p>
            <div className="relative w-32 h-32 flex items-center justify-center rounded-full border-8 border-green-500 text-3xl font-bold text-gray-800">
              {recognition_metrics.success_rate}%
            </div>
            <p className="text-xs text-gray-400 mt-4">{attendance_metrics.successful_scans} / {attendance_metrics.total_scans} scans</p>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col items-center justify-center">
            <p className="text-sm font-medium text-gray-500 mb-2">Failure Rate</p>
            <div className="relative w-32 h-32 flex items-center justify-center rounded-full border-8 border-red-500 text-3xl font-bold text-gray-800">
              {recognition_metrics.failure_rate}%
            </div>
            <p className="text-xs text-gray-400 mt-4">{attendance_metrics.failed_scans} / {attendance_metrics.total_scans} scans</p>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-gray-500" />
          Hardware Profiling
        </h2>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full text-left border-collapse">
            <tbody className="divide-y divide-gray-100">
              <tr className="hover:bg-gray-50">
                <td className="p-4 text-sm font-medium text-gray-600 w-1/3">Average Verification Time</td>
                <td className="p-4 font-bold text-gray-900">{performance_metrics.avg_verification_time_ms} ms</td>
              </tr>
              <tr className="hover:bg-gray-50">
                <td className="p-4 text-sm font-medium text-gray-600">Hardware Queue Status</td>
                <td className="p-4 font-bold text-gray-900">Idle (0 items)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
