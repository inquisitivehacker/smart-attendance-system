import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { CheckCircle2, XCircle, Clock } from 'lucide-react'
import { clsx } from 'clsx'

// Fetch live attendance feed
const fetchLiveFeed = async () => {
  const { data } = await axios.get('/api/attendance/live?limit=50')
  return data
}

export default function LiveMonitor() {
  // Poll every 3 seconds for near-real-time feel
  const { data: scans, isLoading, isError } = useQuery({
    queryKey: ['liveAttendance'],
    queryFn: fetchLiveFeed,
    refetchInterval: 3000 
  })

  if (isLoading) return <div className="text-gray-500">Loading live feed...</div>
  if (isError) return <div className="text-red-500">Failed to load live feed.</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Live Attendance Monitor</h1>
        <div className="flex items-center gap-2 text-sm text-gray-500 bg-white px-3 py-1 rounded-full border shadow-sm">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
          Live Polling Active
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-gray-600 text-sm">
              <th className="p-4 font-medium">Time</th>
              <th className="p-4 font-medium">Student Name</th>
              <th className="p-4 font-medium">Student ID</th>
              <th className="p-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {scans?.length === 0 && (
              <tr>
                <td colSpan={4} className="p-8 text-center text-gray-500">
                  No scans recorded today.
                </td>
              </tr>
            )}
            {scans?.map((scan: any) => (
              <tr 
                key={scan.id} 
                className={clsx(
                  "transition-colors hover:bg-gray-50",
                  scan.face_verified ? "" : "bg-red-50 hover:bg-red-100"
                )}
              >
                <td className="p-4 text-sm text-gray-600 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  {new Date(scan.scanned_at).toLocaleTimeString()}
                </td>
                <td className="p-4 font-medium text-gray-900">{scan.student_name}</td>
                <td className="p-4 text-sm text-gray-500">{scan.student_id}</td>
                <td className="p-4">
                  {scan.face_verified ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm font-medium bg-green-100 text-green-800">
                      <CheckCircle2 className="w-4 h-4" />
                      Verified
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm font-medium bg-red-100 text-red-800">
                      <XCircle className="w-4 h-4" />
                      Failed
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
