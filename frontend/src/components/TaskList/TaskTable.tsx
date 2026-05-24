'use client'

import { Play, Trash2, ExternalLink, RefreshCw, Clock } from 'lucide-react'
import clsx from 'clsx'
import type { Task } from '@/lib/api'

interface TaskTableProps {
  tasks: Task[]
  loading?: boolean
  onPlay?: (task: Task) => void
  onDelete?: (id: string) => void
  onRefresh?: (id: string) => void
  compact?: boolean
}

const statusDisplay = {
  pending: {
    label: 'Pending',
    className: 'status-badge-pending',
    icon: Clock,
  },
  processing: {
    label: 'Processing',
    className: 'status-badge-processing',
    icon: RefreshCw,
  },
  completed: {
    label: 'Completed',
    className: 'status-badge-completed',
    icon: Play,
  },
  failed: {
    label: 'Failed',
    className: 'status-badge-failed',
    icon: Play,
  },
}

export default function TaskTable({
  tasks,
  loading = false,
  onPlay,
  onDelete,
  onRefresh,
  compact = false,
}: TaskTableProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse rounded-lg bg-slate-800/50 h-16" />
        ))}
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="rounded-full bg-slate-800 p-4 mb-3">
          <RefreshCw className="h-6 w-6 text-slate-500" />
        </div>
        <p className="text-sm font-medium text-slate-400">No tasks yet</p>
        <p className="text-xs text-slate-500 mt-1">Create your first video to get started</p>
      </div>
    )
  }

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3">
              Title
            </th>
            {!compact && (
              <>
                <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3">
                  Platform
                </th>
                <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3">
                  Style
                </th>
              </>
            )}
            <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3">
              Status
            </th>
            <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3">
              Progress
            </th>
            {!compact && (
              <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3">
                Created
              </th>
            )}
            <th className="text-right text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/50">
          {tasks.map((task) => {
            const statusInfo = statusDisplay[task.status]
            const StatusIcon = statusInfo.icon
            return (
              <tr
                key={task.id}
                className="hover:bg-slate-800/30 transition-colors group"
              >
                <td className="px-4 py-3">
                  <p className="text-sm font-medium text-slate-200 truncate max-w-[200px]">
                    {task.title || task.product_description?.slice(0, 60) || 'Untitled'}
                  </p>
                </td>
                {!compact && (
                  <>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-400">
                        {task.platform || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-400">
                        {task.style || '-'}
                      </span>
                    </td>
                  </>
                )}
                <td className="px-4 py-3">
                  <span className={clsx('status-badge', statusInfo.className)}>
                    {task.status === 'processing' ? (
                      <StatusIcon className="h-3 w-3 animate-spin" />
                    ) : (
                      <StatusIcon className="h-3 w-3" />
                    )}
                    {statusInfo.label}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 rounded-full bg-slate-700 overflow-hidden">
                      <div
                        className={clsx(
                          'h-full rounded-full transition-all duration-500',
                          task.status === 'completed'
                            ? 'bg-green-500'
                            : task.status === 'failed'
                            ? 'bg-red-500'
                            : task.status === 'processing'
                            ? 'bg-indigo-500'
                            : 'bg-slate-600'
                        )}
                        style={{ width: `${task.progress || 0}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500 w-8">
                      {task.progress || 0}%
                    </span>
                  </div>
                </td>
                {!compact && (
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                      <Clock className="h-3 w-3" />
                      {formatDate(task.created_at)}
                    </span>
                  </td>
                )}
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {task.status === 'completed' && task.video_url && (
                      <button
                        onClick={() => onPlay?.(task)}
                        className="p-1.5 rounded-md text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors"
                        title="Play"
                      >
                        <Play className="h-4 w-4" />
                      </button>
                    )}
                    {(task.status === 'pending' || task.status === 'failed') && (
                      <button
                        onClick={() => onRefresh?.(task.id)}
                        className="p-1.5 rounded-md text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 transition-colors"
                        title="Retry"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </button>
                    )}
                    {task.status === 'completed' && task.video_url && (
                      <a
                        href={task.video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
                        title="Open"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                    <button
                      onClick={() => onDelete?.(task.id)}
                      className="p-1.5 rounded-md text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
