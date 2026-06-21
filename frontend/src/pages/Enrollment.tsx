import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { ShieldCheck, AlertTriangle, XOctagon } from 'lucide-react'

const fetchEnrollment = async () => {
  const { data } = await axios.get('/api/students/enrollment')
  return data
}

export default function Enrollment() {
  const { data: students, isLoading } = useQuery({
    queryKey: ['enrollment'],
    queryFn: fetchEnrollment,
  })

  if (isLoading) return <div>Loading enrollment status...</div>

  // Calculate summaries
  const healthyCount = students?.filter((s: any) => s.status === 'Healthy').length || 0
  const warningCount = students?.filter((s: any) => s.status === 'Warning').length || 0
  const missingCount = students?.filter((s: any) => s.status === 'Missing').length || 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Face Enrollment Status</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-green-100 flex items-center gap-4">
          <div className="p-3 bg-green-50 rounded-lg text-green-600"><ShieldCheck className="w-6 h-6" /></div>
          <div><p className="text-sm font-medium text-gray-500">Healthy (3+ images)</p><p className="text-2xl font-bold">{healthyCount}</p></div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-yellow-100 flex items-center gap-4">
          <div className="p-3 bg-yellow-50 rounded-lg text-yellow-600"><AlertTriangle className="w-6 h-6" /></div>
          <div><p className="text-sm font-medium text-gray-500">Warning (1-2 images)</p><p className="text-2xl font-bold">{warningCount}</p></div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-red-100 flex items-center gap-4">
          <div className="p-3 bg-red-50 rounded-lg text-red-600"><XOctagon className="w-6 h-6" /></div>
          <div><p className="text-sm font-medium text-gray-500">Missing (0 images)</p><p className="text-2xl font-bold">{missingCount}</p></div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-gray-600 text-sm">
              <th className="p-4 font-medium">Student ID</th>
              <th className="p-4 font-medium">Name</th>
              <th className="p-4 font-medium">Images Enrolled</th>
              <th className="p-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {students?.map((student: any) => (
              <tr key={student.id} className="hover:bg-gray-50">
                <td className="p-4 text-sm text-gray-500 font-mono">{student.id}</td>
                <td className="p-4 font-medium text-gray-900">{student.name}</td>
                <td className="p-4 text-sm font-medium">{student.image_count}</td>
                <td className="p-4">
                  <StatusBadge status={student.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'Healthy') {
    return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm font-medium bg-green-100 text-green-800"><ShieldCheck className="w-4 h-4"/> Healthy</span>
  }
  if (status === 'Warning') {
    return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm font-medium bg-yellow-100 text-yellow-800"><AlertTriangle className="w-4 h-4"/> Warning</span>
  }
  return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm font-medium bg-red-100 text-red-800"><XOctagon className="w-4 h-4"/> Missing</span>
}
