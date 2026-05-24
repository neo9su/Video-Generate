'use client'

import { Play, Clock, Download, Trash2, ExternalLink } from 'lucide-react'
import clsx from 'clsx'

interface VideoCardProps {
  id: string
  title: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  thumbnailUrl?: string
  videoUrl?: string
  createdAt: string
  platform?: string
  onPlay?: (id: string) => void
  onDelete?: (id: string) => void
}

const statusConfig = {
  pending: { label: 'Pending', color: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-400/20' },
  processing: { label: 'Processing', color: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/20' },
  completed: { label: 'Completed', color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/20' },
  failed: { label: 'Failed', color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/20' },
}

export default function VideoCard({
  id,
  title,
  status,
  progress,
  thumbnailUrl,
  videoUrl,
  createdAt,
  platform,
  onPlay,
  onDelete,
}: VideoCardProps) {
  const statusInfo = statusConfig[status]

  return (
    <div className={clsx('glass-card overflow-hidden group', status === 'failed' && 'border-red-500/30')}>
      {/* Thumbnail */}
      <div className="relative aspect-video bg-slate-800 overflow-hidden">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className={clsx('rounded-full p-4', status === 'processing' ? 'bg-blue-500/20' : 'bg-slate-700')}>
              <Play className={clsx('h-8 w-8', status === 'processing' ? 'text-blue-400' : 'text-slate-500')} />
            </div>
          </div>
        )}

        {/* Status badge */}
        <div className="absolute top-2 left-2">
          <span className={clsx('status-badge', statusInfo.bg, statusInfo.color, statusInfo.border)}>
            {status === 'processing' && (
              <span className="flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-400" />
              </span>
            )}
            {statusInfo.label}
          </span>
        </div>

        {/* Platform badge */}
        {platform && (
          <div className="absolute top-2 right-2">
            <span className="inline-flex items-center rounded-full bg-slate-900/80 px-2 py-0.5 text-xs font-medium text-slate-300 backdrop-blur-sm border border-slate-700/50">
              {platform}
            </span>
          </div>
        )}

        {/* Hover overlay */}
        {status === 'completed' && videoUrl && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <button
              onClick={() => onPlay?.(id)}
              className="rounded-full bg-white/20 backdrop-blur-sm p-3 hover:bg-white/30 transition-colors"
            >
              <Play className="h-6 w-6 text-white" fill="white" />
            </button>
          </div>
        )}

        {/* Progress bar */}
        {status === 'processing' && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-700">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <h3 className="text-sm font-semibold text-slate-100 truncate">{title || 'Untitled Video'}</h3>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {createdAt}
          </span>
          {progress > 0 && status !== 'completed' && (
            <span className="text-indigo-400">{progress}%</span>
          )}
        </div>

        {/* Actions */}
        <div className="mt-3 flex items-center gap-2">
          {status === 'completed' && videoUrl && (
            <>
              <button
                onClick={() => onPlay?.(id)}
                className="flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-indigo-400 hover:bg-indigo-500/10 transition-colors"
              >
                <Play className="h-3 w-3" />
                Play
              </button>
              <a
                href={videoUrl}
                download
                className="flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-700 transition-colors"
              >
                <Download className="h-3 w-3" />
                Download
              </a>
              <a
                href={videoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-700 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            </>
          )}
          <button
            onClick={() => onDelete?.(id)}
            className="ml-auto flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <Trash2 className="h-3 w-3" />
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
