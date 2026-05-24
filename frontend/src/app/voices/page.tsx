'use client'

import { useState, useEffect, useRef } from 'react'
import {
  Mic,
  Upload,
  Play,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Music,
  StopCircle,
  Clock,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getVoices, cloneVoice, recordVoice, deleteVoice, type Voice } from '@/lib/api'

export default function VoicesPage() {
  const [voices, setVoices] = useState<Voice[]>([])
  const [loading, setLoading] = useState(true)
  const [cloning, setCloning] = useState(false)
  const [recording, setRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioPreview, setAudioPreview] = useState<string | null>(null)
  const [playingId, setPlayingId] = useState<number | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const MAX_RECORD_SECONDS = 10

  useEffect(() => {
    fetchVoices()
  }, [])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (audioPreview) URL.revokeObjectURL(audioPreview)
    }
  }, [audioPreview])

  const fetchVoices = async () => {
    setLoading(true)
    try {
      const data = await getVoices()
      setVoices(data)
    } catch {
      toast.error('Failed to load voices')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    const validTypes = ['audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/mp3', 'audio/ogg', 'audio/webm']
    if (!validTypes.includes(file.type) && !file.name.match(/\.(wav|mp3|ogg|webm|m4a)$/i)) {
      toast.error('Please upload a valid audio file (WAV, MP3, OGG, WebM)')
      return
    }

    setCloning(true)
    try {
      const result = await cloneVoice(file, file.name.replace(/\.[^/.]+$/, ''))
      setVoices((prev) => [result, ...prev])
      toast.success('Voice cloned successfully!')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to clone voice'
      toast.error(message)
    } finally {
      setCloning(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach((t) => t.stop())

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const url = URL.createObjectURL(blob)
        setAudioPreview(url)

        // Auto-clone
        setCloning(true)
        try {
          const result = await recordVoice(blob, `Recorded Voice (${new Date().toLocaleTimeString()})`)
          setVoices((prev) => [result, ...prev])
          toast.success('Voice recorded and cloned!')
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : 'Failed to record voice'
          toast.error(message)
        } finally {
          setCloning(false)
        }
      }

      mediaRecorder.start()
      setRecording(true)
      setRecordingTime(0)

      // Timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => {
          if (prev >= MAX_RECORD_SECONDS) {
            stopRecording()
            return MAX_RECORD_SECONDS
          }
          return prev + 1
        })
      }, 1000)
    } catch (err) {
      toast.error('Microphone access denied. Please allow microphone permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setRecording(false)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this voice?')) return

    try {
      await deleteVoice(id)
      setVoices((prev) => prev.filter((v) => v.id !== id))
      toast.success('Voice deleted')
    } catch {
      toast.error('Failed to delete voice')
    }
  }

  const handlePlayPreview = (voice: Voice) => {
    if (playingId === voice.id) {
      setPlayingId(null)
      return
    }

    if (voice.file_path) {
      // For server-based files, we'd need a streaming URL
      // For now, just show a toast since we may not have direct access
      toast('Preview available for uploaded files', { icon: '🎵' })
    }
    setPlayingId(voice.id)
    setTimeout(() => setPlayingId(null), 2000)
  }

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto animate-fade-in">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Mic className="h-6 w-6 text-indigo-400" />
          Voice Management
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Upload audio files or record your voice to create custom AI narration voices for your videos.
        </p>
      </div>

      {/* Action Cards */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Upload */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10">
              <Upload className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Upload Audio File</h3>
              <p className="text-xs text-slate-500">WAV, MP3, or OGG (max 10MB)</p>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            onChange={handleFileUpload}
            className="hidden"
            id="audio-upload"
          />
          <label
            htmlFor="audio-upload"
            className="flex items-center justify-center gap-2 w-full rounded-lg border-2 border-dashed border-slate-700 hover:border-indigo-500/50 p-4 cursor-pointer transition-colors"
          >
            {cloning ? (
              <Loader2 className="h-5 w-5 text-indigo-400 animate-spin" />
            ) : (
              <Upload className="h-5 w-5 text-slate-400" />
            )}
            <span className="text-sm text-slate-400">
              {cloning ? 'Cloning voice...' : 'Click to select audio file'}
            </span>
          </label>
        </div>

        {/* Record */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-500/10">
              <Mic className="h-5 w-5 text-red-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Record Voice</h3>
              <p className="text-xs text-slate-500">Record up to 10 seconds of speech</p>
            </div>
          </div>

          {recording ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-sm text-red-400 font-medium">Recording...</span>
                </div>
                <span className="text-sm text-slate-300">{formatDuration(recordingTime)} / {formatDuration(MAX_RECORD_SECONDS)}</span>
              </div>
              {/* Progress bar */}
              <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className="h-full rounded-full bg-red-500 transition-all duration-300"
                  style={{ width: `${(recordingTime / MAX_RECORD_SECONDS) * 100}%` }}
                />
              </div>
              <button
                onClick={stopRecording}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 text-sm font-medium hover:bg-red-500/20 transition-colors"
              >
                <StopCircle className="h-4 w-4" />
                Stop Recording
              </button>
            </div>
          ) : cloning ? (
            <div className="flex items-center justify-center gap-2 p-4">
              <Loader2 className="h-5 w-5 text-indigo-400 animate-spin" />
              <span className="text-sm text-slate-400">Cloning voice from recording...</span>
            </div>
          ) : (
            <button
              onClick={startRecording}
              className="w-full flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-700 hover:border-red-500/50 p-4 cursor-pointer transition-colors"
            >
              <Mic className="h-5 w-5 text-slate-400" />
              <span className="text-sm text-slate-400">Click to start recording</span>
            </button>
          )}

          {/* Preview */}
          {audioPreview && !recording && (
            <div className="mt-3 glass-card p-3">
              <p className="text-xs text-slate-500 mb-2">Preview recording:</p>
              <audio src={audioPreview} controls className="w-full h-8" />
            </div>
          )}
        </div>
      </div>

      {/* Voices List */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Music className="h-5 w-5 text-indigo-400" />
          Your Cloned Voices ({voices.length})
        </h2>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
          </div>
        ) : voices.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <Mic className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 font-medium">No voices yet</p>
            <p className="text-sm text-slate-500 mt-1">
              Upload an audio file or record your voice above to create a custom voice.
            </p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {voices.map((voice) => (
              <div
                key={voice.id}
                className="glass-card p-4 hover:border-indigo-500/30 transition-all duration-200"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10">
                      <Music className="h-5 w-5 text-indigo-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-200">{voice.name}</p>
                      <p className="text-xs text-slate-500">
                        {voice.voice_type === 'cloned' ? 'Cloned Voice' : voice.voice_type}
                        {voice.is_default ? ' · Default' : ''}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(voice.id)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Delete voice"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
                  <Clock className="h-3 w-3" />
                  <span>
                    {voice.created_at
                      ? new Date(voice.created_at).toLocaleDateString()
                      : 'Recently'}
                  </span>
                </div>

                {voice.file_path && (
                  <button
                    onClick={() => handlePlayPreview(voice)}
                    className="w-full flex items-center justify-center gap-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-2 text-xs font-medium transition-colors"
                  >
                    {playingId === voice.id ? (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      <>
                        <Play className="h-3 w-3" />
                        Preview Voice
                      </>
                    )}
                  </button>
                )}

                {voice.description && (
                  <p className="text-xs text-slate-600 mt-2 line-clamp-2">{voice.description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
