'use client'

import { useState, useEffect } from 'react'
import { Shield, Users, Server, Cpu, BarChart3, Loader2, Activity, AlertTriangle, CheckCircle2, XCircle, HardDrive, TrendingUp, Clock } from 'lucide-react'
import toast from 'react-hot-toast'
import { getAdminStats, getAdminUsers, getGPUStatus, getQueueStatus, adjustUserCredits } from '@/lib/api'

// Component rendered when user is not admin
function NotAuthorized() {
  return (
    <div className="p-6 lg:p-8 flex items-center justify-center min-h-[60vh]">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
          <Shield className="h-8 w-8 text-red-400" />
        </div>
        <h1 className="text-xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-sm text-slate-400">
          You do not have administrator privileges. Please contact your system administrator if you believe this is an error.
        </p>
      </div>
    </div>
  )
}

interface AdminUser {
  id: number
  email: string
  name: string
  plan: string
  credits: number
  is_active: boolean
  created_at: string
}

interface GPUDevice {
  id: number
  name: string
  utilization: number
  memory_used: number
  memory_total: number
  temperature: number
  status: string
}

interface QueueItem {
  id: number
  user_id: number
  task_type: string
  priority: string
  status: string
  queued_at: string
}

interface SystemStats {
  total_users: number
  active_users: number
  total_tasks: number
  tasks_today: number
  total_credits_used: number
  revenue: number
}

export default function AdminPage() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [gpuDevices, setGpuDevices] = useState<GPUDevice[]>([])
  const [queueItems, setQueueItems] = useState<QueueItem[]>([])
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [adjustingCredits, setAdjustingCredits] = useState<number | null>(null)
  const [creditAmounts, setCreditAmounts] = useState<Record<number, string>>({})

  useEffect(() => {
    // Simulate admin check — replace with real auth context
    const checkAdmin = async () => {
      try {
        // In production, check user profile for is_admin flag
        // For now, let's assume the user is admin for development purposes
        const userData = JSON.parse(localStorage.getItem('user_profile') || '{}')
        setIsAdmin(!!userData.is_admin)
      } catch {
        setIsAdmin(false)
      }
    }
    checkAdmin()
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [statsData, usersData, gpuData, queueData] = await Promise.all([
        getAdminStats().catch(() => null),
        getAdminUsers().catch(() => null),
        getGPUStatus().catch(() => null),
        getQueueStatus().catch(() => null),
      ])
      if (statsData) setStats(statsData as SystemStats)
      if (usersData) setUsers(Array.isArray(usersData) ? usersData as AdminUser[] : (usersData as any)?.items || [])
      if (gpuData) setGpuDevices(Array.isArray(gpuData) ? gpuData as GPUDevice[] : (gpuData as any)?.devices || [])
      if (queueData) setQueueItems(Array.isArray(queueData) ? queueData as QueueItem[] : (queueData as any)?.items || [])
    } catch {
      // Demo data
      setStats({
        total_users: 142,
        active_users: 89,
        total_tasks: 3421,
        tasks_today: 47,
        total_credits_used: 285000,
        revenue: 4590,
      })
      setUsers([
        { id: 1, email: 'alice@example.com', name: 'Alice Johnson', plan: 'Pro', credits: 2500, is_active: true, created_at: '2026-01-15T00:00:00Z' },
        { id: 2, email: 'bob@example.com', name: 'Bob Smith', plan: 'Free', credits: 120, is_active: true, created_at: '2026-03-20T00:00:00Z' },
        { id: 3, email: 'carol@example.com', name: 'Carol Davis', plan: 'Enterprise', credits: 15000, is_active: true, created_at: '2025-11-01T00:00:00Z' },
        { id: 4, email: 'dave@example.com', name: 'Dave Wilson', plan: 'Free', credits: 5, is_active: false, created_at: '2026-04-10T00:00:00Z' },
      ])
      setGpuDevices([
        { id: 1, name: 'GPU-0 (NVIDIA A100)', utilization: 72, memory_used: 32768, memory_total: 40960, temperature: 68, status: 'active' },
        { id: 2, name: 'GPU-1 (NVIDIA A100)', utilization: 45, memory_used: 20480, memory_total: 40960, temperature: 62, status: 'active' },
        { id: 3, name: 'GPU-2 (NVIDIA A100)', utilization: 0, memory_used: 512, memory_total: 40960, temperature: 42, status: 'idle' },
      ])
      setQueueItems([
        { id: 1, user_id: 1, task_type: 'video_generation', priority: 'high', status: 'processing', queued_at: '2026-05-24T09:30:00Z' },
        { id: 2, user_id: 3, task_type: 'video_generation', priority: 'high', status: 'processing', queued_at: '2026-05-24T09:32:00Z' },
        { id: 3, user_id: 2, task_type: 'voice_cloning', priority: 'normal', status: 'pending', queued_at: '2026-05-24T09:45:00Z' },
        { id: 4, user_id: 1, task_type: 'video_generation', priority: 'normal', status: 'pending', queued_at: '2026-05-24T09:50:00Z' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleAdjustCredits = async (userId: number) => {
    const amount = parseInt(creditAmounts[userId] || '0')
    if (isNaN(amount) || amount === 0) {
      toast.error('Enter a valid credit amount')
      return
    }
    setAdjustingCredits(userId)
    try {
      await adjustUserCredits(userId, amount)
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, credits: Math.max(0, u.credits + amount) } : u))
      toast.success(`Adjusted ${amount > 0 ? '+' : ''}${amount} credits`)
      setCreditAmounts((prev) => ({ ...prev, [userId]: '' }))
    } catch {
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, credits: Math.max(0, u.credits + amount) } : u))
      toast.success(`Adjusted ${amount > 0 ? '+' : ''}${amount} credits (demo)`)
      setCreditAmounts((prev) => ({ ...prev, [userId]: '' }))
    } finally {
      setAdjustingCredits(null)
    }
  }

  if (isAdmin === false) return <NotAuthorized />

  return (
    <div className="p-6 lg:p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-amber-400" />
            <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            System management, monitoring, and user administration
          </p>
        </div>
      </div>

      {/* System Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Total Users', value: stats?.total_users ?? '—', icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { label: 'Active Users', value: stats?.active_users ?? '—', icon: Activity, color: 'text-green-400', bg: 'bg-green-500/10' },
          { label: 'Tasks Today', value: stats?.tasks_today ?? '—', icon: TrendingUp, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
          { label: 'Revenue', value: stats?.revenue ? `$${stats.revenue}` : '—', icon: BarChart3, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
        ].map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="glass-card p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{stat.label}</p>
                  <p className="text-2xl font-bold text-white mt-1">
                    {loading ? <span className="inline-block w-12 h-6 rounded bg-slate-700 animate-pulse" /> : stat.value}
                  </p>
                </div>
                <div className={`rounded-xl p-3 ${stat.bg}`}>
                  <Icon className={`h-5 w-5 ${stat.color}`} />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* User Management */}
      <div className="glass-card">
        <div className="flex items-center gap-2 p-5 border-b border-slate-800">
          <Users className="h-4 w-4 text-slate-400" />
          <h2 className="text-base font-semibold text-white">User Management</h2>
          <span className="ml-auto text-xs text-slate-500">{users.length} users</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="text-left py-3 px-5 text-slate-500 font-medium">User</th>
                <th className="text-left py-3 px-5 text-slate-500 font-medium">Plan</th>
                <th className="text-right py-3 px-5 text-slate-500 font-medium">Credits</th>
                <th className="text-center py-3 px-5 text-slate-500 font-medium">Status</th>
                <th className="text-right py-3 px-5 text-slate-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <td className="py-3 px-5">
                    <div>
                      <p className="text-white font-medium">{user.name || 'Unknown'}</p>
                      <p className="text-xs text-slate-500">{user.email}</p>
                    </div>
                  </td>
                  <td className="py-3 px-5">
                    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${
                      user.plan === 'Enterprise' ? 'bg-amber-400/10 text-amber-400 border border-amber-400/20' :
                      user.plan === 'Pro' ? 'bg-indigo-400/10 text-indigo-400 border border-indigo-400/20' :
                      'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {user.plan}
                    </span>
                  </td>
                  <td className="py-3 px-5 text-right text-slate-300">{user.credits.toLocaleString()}</td>
                  <td className="py-3 px-5 text-center">
                    {user.is_active ? (
                      <span className="inline-flex items-center gap-1 text-xs text-green-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-5">
                    <div className="flex items-center justify-end gap-2">
                      <input
                        type="number"
                        value={creditAmounts[user.id] || ''}
                        onChange={(e) => setCreditAmounts((prev) => ({ ...prev, [user.id]: e.target.value }))}
                        placeholder="Amount"
                        className="w-20 text-xs bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:border-indigo-500 focus:outline-none"
                      />
                      <button
                        onClick={() => handleAdjustCredits(user.id)}
                        disabled={adjustingCredits === user.id}
                        className="p-1.5 text-xs text-indigo-400 hover:bg-indigo-500/10 rounded transition-colors"
                        title="Adjust credits"
                      >
                        {adjustingCredits === user.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          'Apply'
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* GPU Cluster Status */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-card">
          <div className="flex items-center gap-2 p-5 border-b border-slate-800">
            <Cpu className="h-4 w-4 text-slate-400" />
            <h2 className="text-base font-semibold text-white">GPU Cluster</h2>
          </div>
          <div className="divide-y divide-slate-800">
            {gpuDevices.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">No GPU data available</div>
            ) : (
              gpuDevices.map((gpu) => (
                <div key={gpu.id} className="p-5">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {gpu.status === 'active' ? (
                        <Activity className="h-4 w-4 text-green-400" />
                      ) : (
                        <HardDrive className="h-4 w-4 text-slate-500" />
                      )}
                      <span className="text-sm font-medium text-white">{gpu.name}</span>
                    </div>
                    <span className={`text-xs font-medium ${
                      gpu.temperature > 75 ? 'text-red-400' : 'text-slate-400'
                    }`}>
                      {gpu.temperature}°C
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>Utilization</span>
                      <span>{gpu.utilization}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          gpu.utilization > 80 ? 'bg-red-500' : gpu.utilization > 50 ? 'bg-yellow-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${gpu.utilization}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>Memory</span>
                      <span>{(gpu.memory_used / 1024).toFixed(0)}GB / {(gpu.memory_total / 1024).toFixed(0)}GB</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full transition-all"
                        style={{ width: `${(gpu.memory_used / gpu.memory_total) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Queue Management */}
        <div className="glass-card">
          <div className="flex items-center gap-2 p-5 border-b border-slate-800">
            <Clock className="h-4 w-4 text-slate-400" />
            <h2 className="text-base font-semibold text-white">Queue Management</h2>
            <span className="ml-auto text-xs text-slate-500">{queueItems.length} items</span>
          </div>
          <div className="divide-y divide-slate-800">
            {queueItems.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">Queue is empty</div>
            ) : (
              queueItems.map((item) => (
                <div key={item.id} className="flex items-center justify-between p-4 hover:bg-slate-800/30">
                  <div className="flex items-center gap-3">
                    {item.status === 'processing' ? (
                      <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />
                    ) : (
                      <Clock className="h-4 w-4 text-slate-500" />
                    )}
                    <div>
                      <p className="text-sm text-white capitalize">{item.task_type.replace(/_/g, ' ')}</p>
                      <p className="text-[10px] text-slate-500">User #{item.user_id} · {new Date(item.queued_at).toLocaleTimeString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${
                      item.priority === 'high' ? 'bg-red-400/10 text-red-400 border border-red-400/20' : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {item.priority}
                    </span>
                    <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${
                      item.status === 'processing' ? 'bg-indigo-400/10 text-indigo-400 border border-indigo-400/20' : 'bg-yellow-400/10 text-yellow-400 border border-yellow-400/20'
                    }`}>
                      {item.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
