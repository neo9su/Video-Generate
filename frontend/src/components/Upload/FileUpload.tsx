'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, File, Image, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadFile } from '@/lib/api'
import clsx from 'clsx'

interface FileItem {
  file: File
  preview?: string
  url?: string
  progress: number
  status: 'pending' | 'uploading' | 'done' | 'error'
  error?: string
}

interface FileUploadProps {
  onFilesReady?: (urls: string[]) => void
  maxFiles?: number
  accept?: Record<string, string[]>
}

export default function FileUpload({
  onFilesReady,
  maxFiles = 10,
  accept = { 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] },
}: FileUploadProps) {
  const [files, setFiles] = useState<FileItem[]>([])

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const remaining = maxFiles - files.length
      const newFiles = acceptedFiles.slice(0, remaining).map((file) => ({
        file,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
        progress: 0,
        status: 'pending' as const,
      }))
      setFiles((prev) => [...prev, ...newFiles])
    },
    [files.length, maxFiles]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxFiles,
    disabled: files.length >= maxFiles,
  })

  const handleUpload = async (index: number) => {
    const item = files[index]
    if (!item || item.status !== 'pending') return

    setFiles((prev) => {
      const updated = [...prev]
      updated[index] = { ...updated[index], status: 'uploading' }
      return updated
    })

    try {
      const result = await uploadFile(item.file, (percent) => {
        setFiles((prev) => {
          const updated = [...prev]
          updated[index] = { ...updated[index], progress: percent }
          return updated
        })
      })
      setFiles((prev) => {
        const updated = [...prev]
        updated[index] = { ...updated[index], status: 'done', progress: 100, url: result.url }
        return updated
      })
      const urls = files
        .map((f, i) => (i === index ? result.url : f.url))
        .filter(Boolean) as string[]
      onFilesReady?.(urls)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setFiles((prev) => {
        const updated = [...prev]
        updated[index] = { ...updated[index], status: 'error', error: message }
        return updated
      })
    }
  }

  const handleUploadAll = () => {
    files.forEach((item, index) => {
      if (item.status === 'pending') handleUpload(index)
    })
  }

  const removeFile = (index: number) => {
    setFiles((prev) => {
      const updated = prev.filter((_, i) => i !== index)
      onFilesReady?.(updated.filter((f) => f.url).map((f) => f.url!) )
      return updated
    })
  }

  const allDone = files.length > 0 && files.every((f) => f.status === 'done')
  const hasPending = files.some((f) => f.status === 'pending')

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all duration-200 cursor-pointer',
          isDragActive
            ? 'border-indigo-500 bg-indigo-500/5'
            : files.length >= maxFiles
            ? 'border-slate-600 bg-slate-800/50 cursor-not-allowed opacity-60'
            : 'border-slate-600 bg-slate-800/50 hover:border-slate-500 hover:bg-slate-800'
        )}
      >
        <input {...getInputProps()} />
        <div className={clsx('rounded-full p-3 mb-3', isDragActive ? 'bg-indigo-500/20' : 'bg-slate-700')}>
          <Upload className={clsx('h-6 w-6', isDragActive ? 'text-indigo-400' : 'text-slate-400')} />
        </div>
        {isDragActive ? (
          <p className="text-sm font-medium text-indigo-400">Drop files here...</p>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-300">
              {files.length >= maxFiles
                ? 'Max files reached'
                : 'Drag & drop product images here'}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              PNG, JPG, WebP up to 10MB each ({maxFiles - files.length} remaining)
            </p>
          </>
        )}
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item, index) => (
            <div
              key={`${item.file.name}-${index}`}
              className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-800/50 p-3 animate-slide-up"
            >
              {/* Preview */}
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-slate-700 overflow-hidden">
                {item.preview ? (
                  <img src={item.preview} alt="" className="h-full w-full object-cover" />
                ) : (
                  <File className="h-5 w-5 text-slate-400" />
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">{item.file.name}</p>
                <p className="text-xs text-slate-500">
                  {(item.file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                {/* Progress bar */}
                {item.status === 'uploading' && (
                  <div className="mt-1.5 h-1.5 w-full rounded-full bg-slate-700 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-indigo-500 transition-all duration-300"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                )}
              </div>

              {/* Status */}
              <div className="flex items-center gap-2">
                {item.status === 'pending' && (
                  <span className="text-xs text-slate-400">Ready</span>
                )}
                {item.status === 'uploading' && (
                  <span className="text-xs text-indigo-400">{item.progress}%</span>
                )}
                {item.status === 'done' && (
                  <CheckCircle className="h-5 w-5 text-green-400" />
                )}
                {item.status === 'error' && (
                  <div className="group relative">
                    <AlertCircle className="h-5 w-5 text-red-400" />
                    <div className="absolute right-0 top-full mt-1 hidden group-hover:block bg-red-900/90 text-red-200 text-xs rounded-lg px-2 py-1 whitespace-nowrap">
                      {item.error}
                    </div>
                  </div>
                )}
                <button
                  onClick={() => removeFile(index)}
                  className="p-1 rounded-md text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      {files.length > 0 && !allDone && (
        <div className="flex justify-end">
          <button
            onClick={handleUploadAll}
            disabled={!hasPending}
            className="btn-primary"
          >
            <Upload className="h-4 w-4" />
            Upload {hasPending ? `(${files.filter(f => f.status === 'pending').length})` : ''}
          </button>
        </div>
      )}

      {allDone && (
        <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-3 text-center">
          <p className="text-sm text-green-400 font-medium">
            ✓ All {files.length} file{files.length > 1 ? 's' : ''} uploaded successfully
          </p>
        </div>
      )}
    </div>
  )
}
