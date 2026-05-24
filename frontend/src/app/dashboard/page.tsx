'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Film,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Plus,
  TrendingUp,
  Clock,
  ArrowRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getTasks, deleteTask, type Task } from '@/lib/api'
import TaskTable from '@/components/TaskList/TaskTable'

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getTasks({ limit: 20 })
      setTasks(data.items || [])
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load tasks'
      setError(message)
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const stats = {
    total: tasks.length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    processing: tasks.filter((t) => t.status === 'processing').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
  }

  const recentTasks = tasks.slice(0, 10)

  const handleDelete = async (id: string) => {
    try {
      await deleteTask(id)
      toast.success('Task deleted')
      fetchTasks()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete task')
    }
  }

  const handleRefresh = async (id: string) => {
    toast.success('Task refreshed')
  }

  const handlePlay = (task: Task) => {
    if (task.video_url) {
      window.open(task.video_url, '_blank')
    }
  }

  const statCards = [
    {
      label: 'Total Tasks',
      value: stats.total,
      icon: Film,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
    },
    {
      label: 'Completed',
      value: stats.completed,
      icon: CheckCircle2,
      color: 'text-green-400',
      bg: 'bg-green-500/10',
      border: 'border-green-500/20',
    },
    {
      label: 'Processing',
      value: stats.processing,
      icon: Loader2,
      color: 'text-indigo-400',
      bg: 'bg-indigo-500/10',
      border: 'border-indigo-500/20',
    },
    {
      label: 'Failed',
      value: stats.failed,
      icon: AlertCircle,
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
    },
  ]

  return (
    <div className="p-6 lg:p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Overview of your video generation tasks</p>
        </div>
        <Link href="/create" className="btn-primary">
          <Plus className="h-4 w-4" />
          Create Video
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div
              key={stat.label}
              className={`glass-card p-5 ${stat.border} hover:bg-slate-700/30 transition-colors`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {stat.label}
                  </p>
                  <p className="text-3xl font-bold text-white mt-2">
                    {loading ? (
                      <span className="inline-block w-8 h-8 rounded bg-slate-700 animate-pulse" />
                    ) : (
                      stat.value
                    )}
                  </p>
                </div>
                <div className={`rounded-xl p-3 ${stat.bg}`}>
                  <Icon className={`h-5 w-5 ${stat.color}`} />
                </div>
              </div>
              {!loading && stat.label === 'Completed' && stats.total > 0 && (
                <div className="mt-3 flex items-center gap-1 text-xs text-slate-500">
                  <TrendingUp className="h-3 w-3 text-green-400" />
                  <span>
                    {Math.round((stats.completed / stats.total) * 100)}% success rate
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Recent Tasks */}
      <div className="glass-card">
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-slate-400" />
            <h2 className="text-base font-semibold text-white">Recent Tasks</h2>
          </div>
          {tasks.length > 0 && (
            <Link
              href="/tasks"
              className="flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              View all
              <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>

        {error ? (
          <div className="p-8 text-center">
            <AlertCircle className="h-8 w-8 text-red-400 mx-auto mb-3" />
            <p className="text-sm text-red-400 mb-2">Failed to load tasks</p>
            <button onClick={fetchTasks} className="btn-secondary text-xs">
              Retry
            </button>
          </div>
        ) : (
          <div className="p-5">
            <TaskTable
              tasks={recentTasks}
              loading={loading}
              onPlay={handlePlay}
              onDelete={handleDelete}
              onRefresh={handleRefresh}
              compact
            />
            {!loading && tasks.length === 0 && (
              <div className="text-center py-8">
                <Link href="/create" className="btn-primary">
                  <Plus className="h-4 w-4" />
                  Create Your First Video
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
