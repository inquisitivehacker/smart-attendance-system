import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Download, FileText, Users } from 'lucide-react'

const fetchSessionReports = async () => {
  const { data } = await axios.get('/api/reports/sessions')
  return data
}

const fetchStudentReports = async () => {
  const { data } = await axios.get('/api/reports/students')
  return data
}

export default function Reports() {
  const [activeTab, setActiveTab] = useState<'sessions' | 'students'>('sessions')

  const { data: sessionReports, isLoading: isSessionsLoading } = useQuery({
    queryKey: ['sessionReports'],
    queryFn: fetchSessionReports,
    enabled: activeTab === 'sessions'
  })

  const { data: studentReports, isLoading: isStudentsLoading } = useQuery({
    queryKey: ['studentReports'],
    queryFn: fetchStudentReports,
    enabled: activeTab === 'students'
  })

  const handleExport = () => {
    window.location.href = '/api/reports/export/csv'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Attendance Reports</h1>
        <button 
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('sessions')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'sessions' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}
        >
          <FileText className="w-4 h-4" />
          By Session
        </button>
        <button
          onClick={() => setActiveTab('students')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'students' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}
        >
          <Users className="w-4 h-4" />
          By Student
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {activeTab === 'sessions' && (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b text-gray-600 text-sm">
                <th className="p-4 font-medium">Date & Time</th>
                <th className="p-4 font-medium">Subject</th>
                <th className="p-4 font-medium">Present</th>
                <th className="p-4 font-medium">Absent</th>
                <th className="p-4 font-medium">Attendance %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isSessionsLoading ? <tr><td colSpan={5} className="p-4 text-center">Loading...</td></tr> : null}
              {sessionReports?.map((report: any) => (
                <tr key={report.id} className="hover:bg-gray-50">
                  <td className="p-4 text-sm text-gray-900">{new Date(report.date).toLocaleString()}</td>
                  <td className="p-4 font-medium">{report.subject}</td>
                  <td className="p-4 text-green-600 font-medium">{report.present}</td>
                  <td className="p-4 text-red-600 font-medium">{report.absent}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-full bg-gray-200 rounded-full h-2 max-w-[100px]">
                        <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${report.percentage}%` }}></div>
                      </div>
                      <span className="text-sm text-gray-600">{report.percentage}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'students' && (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b text-gray-600 text-sm">
                <th className="p-4 font-medium">Student ID</th>
                <th className="p-4 font-medium">Name</th>
                <th className="p-4 font-medium">Total Sessions</th>
                <th className="p-4 font-medium">Present</th>
                <th className="p-4 font-medium">Absent</th>
                <th className="p-4 font-medium">Attendance %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isStudentsLoading ? <tr><td colSpan={6} className="p-4 text-center">Loading...</td></tr> : null}
              {studentReports?.map((report: any) => (
                <tr key={report.id} className="hover:bg-gray-50">
                  <td className="p-4 text-sm text-gray-500 font-mono">{report.id}</td>
                  <td className="p-4 font-medium text-gray-900">{report.name}</td>
                  <td className="p-4 text-sm text-gray-600">{report.total_sessions}</td>
                  <td className="p-4 text-green-600 font-medium">{report.present}</td>
                  <td className="p-4 text-red-600 font-medium">{report.absent}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-full bg-gray-200 rounded-full h-2 max-w-[100px]">
                        <div 
                          className={`h-2 rounded-full ${report.percentage < 75 ? 'bg-orange-500' : 'bg-green-500'}`} 
                          style={{ width: `${report.percentage}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-600">{report.percentage}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
