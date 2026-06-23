import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { PlayCircle, StopCircle, Calendar } from 'lucide-react'

const fetchActiveSession = async () => {
  const { data } = await axios.get('/api/sessions/active')
  return data
}

const fetchTodaySessions = async () => {
  const { data } = await axios.get('/api/sessions/today')
  return data
}

export default function Sessions() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({ subject: '', faculty_name: '', room: '' })

  const { data: activeSession, isLoading: isSessionLoading } = useQuery({
    queryKey: ['activeSession'],
    queryFn: fetchActiveSession,
  })

  const { data: todaySessions } = useQuery({
    queryKey: ['todaySessions'],
    queryFn: fetchTodaySessions,
  })

  const startMutation = useMutation({
    mutationFn: (newSession: any) => axios.post('/api/sessions/start', newSession),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activeSession'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
    }
  })

  const endMutation = useMutation({
    mutationFn: () => axios.post('/api/sessions/end'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activeSession'] })
      queryClient.invalidateQueries({ queryKey: ['todaySessions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
    }
  })

  const handleStart = (e: React.FormEvent) => {
    e.preventDefault()
    startMutation.mutate(formData)
  }

  if (isSessionLoading) return <div>Loading session data...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Session Management</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Session Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <PlayCircle className="w-5 h-5 text-blue-500" />
            Active Session
          </h2>
          
          {activeSession ? (
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 rounded-lg text-blue-900">
                <p className="font-bold text-xl">{activeSession.subject}</p>
                <p className="text-sm opacity-80">Faculty: {activeSession.faculty_name} | Room: {activeSession.room}</p>
                <p className="text-sm opacity-80 mt-2">Started: {new Date(activeSession.started_at).toLocaleTimeString()}</p>
              </div>
              <button 
                onClick={() => endMutation.mutate()}
                disabled={endMutation.isPending}
                className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                <StopCircle className="w-5 h-5" />
                End Current Session
              </button>
            </div>
          ) : (
            <form onSubmit={handleStart} className="space-y-4">
              <p className="text-sm text-gray-500 mb-4">Start a new session to begin recording attendance.</p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                <input required type="text" className="w-full border rounded-md p-2" placeholder="e.g. CS101" value={formData.subject} onChange={e => setFormData({...formData, subject: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Faculty Name</label>
                <input required type="text" className="w-full border rounded-md p-2" placeholder="e.g. Dr. Smith" value={formData.faculty_name} onChange={e => setFormData({...formData, faculty_name: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Room</label>
                <input required type="text" className="w-full border rounded-md p-2" placeholder="e.g. Room 302" value={formData.room} onChange={e => setFormData({...formData, room: e.target.value})} />
              </div>
              <button 
                type="submit"
                disabled={startMutation.isPending}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                <PlayCircle className="w-5 h-5" />
                Start Session
              </button>
            </form>
          )}
        </div>

        {/* Today's History Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-gray-500" />
            Today's Sessions
          </h2>
          <div className="space-y-3">
            {todaySessions?.length === 0 && (
              <p className="text-gray-500 italic">No sessions recorded today.</p>
            )}
            {todaySessions?.map((session: any) => (
              <div key={session.id} className="p-3 border rounded-lg flex justify-between items-center hover:bg-gray-50">
                <div>
                  <p className="font-medium text-gray-900">{session.subject}</p>
                  <p className="text-xs text-gray-500">{session.faculty_name} | {session.room}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-700">
                    {new Date(session.started_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} 
                    {session.ended_at ? ` - ${new Date(session.ended_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}` : ' (Active)'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
