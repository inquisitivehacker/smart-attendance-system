import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Trash2, Edit2, Search } from 'lucide-react'

const fetchStudents = async () => {
  const { data } = await axios.get('/api/students/')
  return data
}

export default function Students() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [isEditing, setIsEditing] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ name: '', department: '' })

  const { data: students, isLoading } = useQuery({
    queryKey: ['students'],
    queryFn: fetchStudents,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => axios.delete(`/api/students/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['students'] })
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string, data: any }) => axios.put(`/api/students/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
      setIsEditing(null)
    }
  })

  if (isLoading) return <div>Loading students...</div>

  const filteredStudents = students?.filter((s: any) => 
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.department?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const startEdit = (student: any) => {
    setIsEditing(student.id)
    setEditForm({ name: student.name, department: student.department || '' })
  }

  const saveEdit = (id: string) => {
    updateMutation.mutate({ id, data: editForm })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Student Directory</h1>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search students..." 
              className="pl-9 pr-4 py-2 w-full border rounded-md text-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-gray-600 text-sm">
              <th className="p-4 font-medium">Student ID</th>
              <th className="p-4 font-medium">Name</th>
              <th className="p-4 font-medium">Department</th>
              <th className="p-4 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredStudents?.map((student: any) => (
              <tr key={student.id} className="hover:bg-gray-50">
                <td className="p-4 text-sm text-gray-500 font-mono">{student.id}</td>
                <td className="p-4 font-medium text-gray-900">
                  {isEditing === student.id ? (
                    <input 
                      type="text" 
                      className="border rounded px-2 py-1 w-full"
                      value={editForm.name}
                      onChange={e => setEditForm({...editForm, name: e.target.value})}
                    />
                  ) : student.name}
                </td>
                <td className="p-4 text-sm text-gray-500">
                  {isEditing === student.id ? (
                    <input 
                      type="text" 
                      className="border rounded px-2 py-1 w-full"
                      value={editForm.department}
                      onChange={e => setEditForm({...editForm, department: e.target.value})}
                    />
                  ) : (student.department || '-')}
                </td>
                <td className="p-4 flex items-center gap-3">
                  {isEditing === student.id ? (
                    <>
                      <button onClick={() => saveEdit(student.id)} className="text-green-600 text-sm font-medium">Save</button>
                      <button onClick={() => setIsEditing(null)} className="text-gray-500 text-sm">Cancel</button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => startEdit(student)} className="text-blue-600 hover:text-blue-800">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => deleteMutation.mutate(student.id)} className="text-red-500 hover:text-red-700">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
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
