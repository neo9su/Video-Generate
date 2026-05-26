'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Upload,
  Video,
  User,
  Mic,
  FileText,
  Sparkles,
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
  Download,
  RotateCcw,
  Eye,
  Wand2,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react'
import toast from 'react-hot-toast'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface RemakeTaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  output_data?: {
    video_url?: string
    thumbnail_url?: string
    [key: string]: unknown
  }
  error_message?: string
}

export default function RemakePage() {
  // File states
  const [originalVideo, setOriginalVideo] = useState<File | null>(null)
  const [originalVideoUrl, setOriginalVideoUrl] = useState<string | null>(null)
  const [sourceFace, setSourceFace] = useState<File | null>(null)
  const [sourceFaceUrl, setSourceFaceUrl] = useState<string | null>(null)
  const [voiceSample, setVoiceSample] = useState<File | null>(null)
  const [voiceSampleName, setVoiceSampleName] = useState<string | null>(null)

  // Options
  const [narrationText, setNarrationText] = useState('')
  const [enhanceFace, setEnhanceFace] = useState(true)
  const [generatingFace, setGeneratingFace] = useState(false)

  // Submission & progress
  const [submitting, setSubmitting] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<RemakeTaskStatus | null>(null)
  const [polling, setPolling] = useState(false)

  // Refs
  const videoInputRef = useRef<HTMLInputElement>(null)
  const faceInputRef = useRef<HTMLInputElement>(null)
  const voiceInputRef = useRef<HTMLInputElement>(null)
  const pollingRef = useRef<NodeJS.Timeout | null>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // ─── File Handlers ──────────────────────────────────────────────────────
  const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('video/')) {
      toast.error('Please upload a valid video file')
      return
    }

    if (file.size > 500 * 1024 * 1024) {
      toast.error('Video file must be under 500MB')
      return
    }

    setOriginalVideo(file)
    setOriginalVideoUrl(URL.createObjectURL(file))
    toast.success('Video uploaded successfully')
  }

  const handleFaceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      toast.error('Please upload a valid image file')
      return
    }

    setSourceFace(file)
    setSourceFaceUrl(URL.createObjectURL(file))
    toast.success('Face image uploaded')
  }

  const handleVoiceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const validTypes = ['audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm', 'audio/m4a', 'audio/x-m4a']
    if (!file.type.startsWith('audio/') && !validTypes.includes(file.type)) {
      toast.error('Please upload a valid audio file')
      return
    }

    setVoiceSample(file)
    setVoiceSampleName(file.name)
    toast.success('Voice sample uploaded')
  }

  const handleGenerateAIFace = async () => {
    setGeneratingFace(true)
    try {
      // Simulate AI face generation — in production this would call an endpoint
      await new Promise((resolve) => setTimeout(resolve, 2000))
      toast.success('AI face generated! (Demo mode)')
      // In production, set the generated face image
      // For now, show a placeholder state
      setSourceFaceUrl('/api/placeholder/ai-face')
    } catch {
      toast.error('Failed to generate AI face')
    } finally {
      setGeneratingFace(false)
    }
  }

  const removeVideo = () => {
    setOriginalVideo(null)
    if (originalVideoUrl) URL.revokeObjectURL(originalVideoUrl)
    setOriginalVideoUrl(null)
    if (videoInputRef.current) videoInputRef.current.value = ''
  }

  const removeFace = () => {
    setSourceFace(null)
    if (sourceFaceUrl) URL.revokeObjectURL(sourceFaceUrl)
    setSourceFaceUrl(null)
    if (faceInputRef.current) faceInputRef.current.value = ''
  }

  const removeVoice = () => {
    setVoiceSample(null)
    setVoiceSampleName(null)
    if (voiceInputRef.current) voiceInputRef.current.value = ''
  }

  // ─── Polling ─────────────────────────────────────────────────────────────
  const startPolling = useCallback((id: string) => {
    setPolling(true)

    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/remake/remake/${id}?user_id=1`)
        if (!res.ok) throw new Error('Failed to fetch task status')

        const data: RemakeTaskStatus = await res.json()
        setTaskStatus(data)

        if (data.status === 'completed') {
          if (pollingRef.current) clearInterval(pollingRef.current)
          setPolling(false)
          toast.success('Video remake completed!')
        } else if (data.status === 'failed') {
          if (pollingRef.current) clearInterval(pollingRef.current)
          setPolling(false)
          toast.error(data.error_message || 'Task failed')
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }

    // Poll immediately, then every 3 seconds
    poll()
    pollingRef.current = setInterval(poll, 3000)
  }, [])

  // ─── Submit ──────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!originalVideo) {
      toast.error('Please upload an original video')
      return
    }
    if (!sourceFace && !sourceFaceUrl) {
      toast.error('Please upload or generate a source face')
      return
    }

    setSubmitting(true)
    setTaskStatus(null)
    setTaskId(null)

    try {
      const formData = new FormData()
      formData.append('original_video', originalVideo)
      if (sourceFace) {
        formData.append('source_face', sourceFace)
      }
      if (voiceSample) {
        formData.append('voice_sample', voiceSample)
      }
      formData.append('narration_text', narrationText)
      formData.append('enhance_face', String(enhanceFace))
      formData.append('user_id', '1') // TODO: get from auth context

      const res = await fetch(`${API_BASE_URL}/remake/remake`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || `Server error: ${res.status}`)
      }

      const data = await res.json()
      const newTaskId = data.task_id

      setTaskId(newTaskId)
      setTaskStatus({ task_id: newTaskId, status: 'pending', progress: 0 })
      toast.success('Remake job submitted!')

      // Start polling
      startPolling(newTaskId)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to submit remake job'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleReset = () => {
    if (pollingRef.current) clearInterval(pollingRef.current)
    setPolling(false)
    setTaskId(null)
    setTaskStatus(null)
    removeVideo()
    removeFace()
    removeVoice()
    setNarrationText('')
    setEnhanceFace(true)
  }

  // ─── Progress UI ──────────────────────────────────────────────────────────
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'text-yellow-400'
      case 'processing': return 'text-blue-400'
      case 'completed': return 'text-green-400'
      case 'failed': return 'text-red-400'
      default: return 'text-slate-400'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <Loader2 className="h-5 w-5 text-yellow-400 animate-spin" />
      case 'processing': return <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
      case 'completed': return <CheckCircle2 className="h-5 w-5 text-green-400" />
      case 'failed': return <AlertCircle className="h-5 w-5 text-red-400" />
      default: return null
    }
  }

  const canSubmit = originalVideo && (sourceFace || sourceFaceUrl) && !submitting && !polling

  return (
    <div className="min-h-screen p-6 md:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 to-pink-600 shadow-lg shadow-purple-500/20">
            <Video className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Video Remake</h1>
            <p className="text-sm text-slate-400">
              Swap faces, clone voices, and re-narrate existing videos with AI
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Inputs */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step 1: Original Video Upload */}
          <section className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-sm font-bold text-purple-400">
                1
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-white">Original Video</h3>
                <p className="text-xs text-slate-400">Upload the video you want to remake</p>
              </div>
              {originalVideo && (
                <button onClick={removeVideo} className="p-1.5 rounded-lg hover:bg-slate-700 transition-colors">
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              )}
            </div>

            {!originalVideoUrl ? (
              <div
                onClick={() => videoInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-purple-500/50 hover:bg-purple-500/5 transition-all duration-200"
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-purple-500/10">
                  <Upload className="h-7 w-7 text-purple-400" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-200">Click to upload video</p>
                  <p className="text-xs text-slate-500 mt-1">MP4, MOV, WebM, MKV — up to 500MB</p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl overflow-hidden bg-black/50 border border-slate-700">
                <video
                  src={originalVideoUrl}
                  controls
                  className="w-full max-h-56 object-contain"
                />
                <div className="px-4 py-2 flex items-center justify-between bg-slate-800/50">
                  <span className="text-xs text-slate-300 truncate max-w-[200px]">{originalVideo?.name}</span>
                  <span className="text-xs text-slate-500">
                    {originalVideo && (originalVideo.size / (1024 * 1024)).toFixed(1)}MB
                  </span>
                </div>
              </div>
            )}
            <input
              ref={videoInputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
              onChange={handleVideoUpload}
              className="hidden"
            />
          </section>

          {/* Step 2: Source Face */}
          <section className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-pink-500/10 text-sm font-bold text-pink-400">
                2
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-white">Source Face</h3>
                <p className="text-xs text-slate-400">Upload a face image or generate one with AI</p>
              </div>
              {sourceFace && (
                <button onClick={removeFace} className="p-1.5 rounded-lg hover:bg-slate-700 transition-colors">
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Upload Face */}
              <div
                onClick={() => faceInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 rounded-xl p-6 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-pink-500/50 hover:bg-pink-500/5 transition-all duration-200"
              >
                {sourceFaceUrl && sourceFace ? (
                  <img
                    src={sourceFaceUrl}
                    alt="Source face"
                    className="h-20 w-20 rounded-xl object-cover border-2 border-pink-500/30"
                  />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-pink-500/10">
                    <User className="h-6 w-6 text-pink-400" />
                  </div>
                )}
                <p className="text-xs font-medium text-slate-300">
                  {sourceFace ? 'Change image' : 'Upload face image'}
                </p>
                <p className="text-[10px] text-slate-500">PNG, JPG — clear frontal face</p>
              </div>

              {/* AI Generate */}
              <button
                onClick={handleGenerateAIFace}
                disabled={generatingFace}
                className="border-2 border-dashed border-slate-700 rounded-xl p-6 flex flex-col items-center justify-center gap-2 hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {generatingFace ? (
                  <Loader2 className="h-12 w-12 text-indigo-400 animate-spin" />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-500/10">
                    <Wand2 className="h-6 w-6 text-indigo-400" />
                  </div>
                )}
                <p className="text-xs font-medium text-slate-300">
                  {generatingFace ? 'Generating...' : 'Generate with AI'}
                </p>
                <p className="text-[10px] text-slate-500">Create a synthetic face</p>
              </button>
            </div>
            <input
              ref={faceInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp"
              onChange={handleFaceUpload}
              className="hidden"
            />
          </section>

          {/* Step 3: Voice Sample (Optional) */}
          <section className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-sm font-bold text-blue-400">
                3
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-white">Voice Sample <span className="text-slate-500 font-normal">(Optional)</span></h3>
                <p className="text-xs text-slate-400">Upload an audio file for voice cloning</p>
              </div>
              {voiceSample && (
                <button onClick={removeVoice} className="p-1.5 rounded-lg hover:bg-slate-700 transition-colors">
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              )}
            </div>

            {!voiceSample ? (
              <div
                onClick={() => voiceInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 rounded-xl p-6 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-blue-500/50 hover:bg-blue-500/5 transition-all duration-200"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
                  <Mic className="h-6 w-6 text-blue-400" />
                </div>
                <p className="text-xs font-medium text-slate-300">Upload voice sample</p>
                <p className="text-[10px] text-slate-500">MP3, WAV, M4A — 10s to 5min of clean speech</p>
              </div>
            ) : (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-blue-500/5 border border-blue-500/20">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                  <Mic className="h-5 w-5 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{voiceSampleName}</p>
                  <p className="text-xs text-slate-500">
                    {(voiceSample.size / (1024 * 1024)).toFixed(2)}MB
                  </p>
                </div>
                <CheckCircle2 className="h-5 w-5 text-blue-400 flex-shrink-0" />
              </div>
            )}
            <input
              ref={voiceInputRef}
              type="file"
              accept="audio/mp3,audio/mpeg,audio/wav,audio/ogg,audio/webm,audio/m4a,audio/x-m4a"
              onChange={handleVoiceUpload}
              className="hidden"
            />
          </section>

          {/* Step 4: Narration Text */}
          <section className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-sm font-bold text-emerald-400">
                4
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-white">Narration Text <span className="text-slate-500 font-normal">(Optional)</span></h3>
                <p className="text-xs text-slate-400">Provide narration or leave empty to auto-extract from video</p>
              </div>
            </div>

            <div className="relative">
              <textarea
                value={narrationText}
                onChange={(e) => setNarrationText(e.target.value)}
                placeholder="Enter narration text here, or leave blank to auto-extract from the original video's audio track..."
                className="input-field min-h-[120px] resize-y pr-12"
                rows={4}
              />
              <div className="absolute bottom-3 right-3">
                <span className="text-[10px] text-slate-500">{narrationText.length} chars</span>
              </div>
            </div>

            {!narrationText && (
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                <span>Audio will be auto-transcribed if left empty</span>
              </div>
            )}
          </section>

          {/* Step 5: Face Enhancement Toggle */}
          <section className="glass-card p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-sm font-bold text-amber-400">
                  5
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Face Enhancement</h3>
                  <p className="text-xs text-slate-400">Improve face quality in the output video</p>
                </div>
              </div>

              <button
                onClick={() => setEnhanceFace(!enhanceFace)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
              >
                {enhanceFace ? (
                  <ToggleRight className="h-7 w-7 text-amber-400" />
                ) : (
                  <ToggleLeft className="h-7 w-7 text-slate-500" />
                )}
                <span className={`text-sm font-medium ${enhanceFace ? 'text-amber-400' : 'text-slate-500'}`}>
                  {enhanceFace ? 'Enabled' : 'Disabled'}
                </span>
              </button>
            </div>

            {enhanceFace && (
              <div className="mt-3 ml-11 text-xs text-slate-500 flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-amber-400/60" />
                <span>GFPGAN/CodeFormer will be applied to enhance facial details</span>
              </div>
            )}
          </section>
        </div>

        {/* Right Column - Summary & Submit */}
        <div className="space-y-6">
          {/* Summary Card */}
          <div className="glass-card p-6 sticky top-6">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <Eye className="h-4 w-4 text-slate-400" />
              Job Summary
            </h3>

            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Video</span>
                <span className={`font-medium ${originalVideo ? 'text-green-400' : 'text-slate-600'}`}>
                  {originalVideo ? '✓ Ready' : '—'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Face</span>
                <span className={`font-medium ${sourceFace || sourceFaceUrl ? 'text-green-400' : 'text-slate-600'}`}>
                  {sourceFace ? '✓ Uploaded' : sourceFaceUrl ? '✓ Generated' : '—'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Voice</span>
                <span className={`font-medium ${voiceSample ? 'text-green-400' : 'text-slate-600'}`}>
                  {voiceSample ? '✓ Ready' : 'Not set'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Narration</span>
                <span className={`font-medium ${narrationText ? 'text-green-400' : 'text-slate-600'}`}>
                  {narrationText ? '✓ Custom' : 'Auto-extract'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Enhancement</span>
                <span className={`font-medium ${enhanceFace ? 'text-amber-400' : 'text-slate-600'}`}>
                  {enhanceFace ? 'On' : 'Off'}
                </span>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-700/50">
              <button
                onClick={handleSubmit}
                disabled={!canSubmit}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold text-sm shadow-lg shadow-purple-500/20 hover:shadow-purple-500/40 hover:from-purple-500 hover:to-pink-500 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Start Remake
                  </>
                )}
              </button>

              {taskId && (
                <button
                  onClick={handleReset}
                  className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-sm hover:bg-slate-800 transition-colors"
                >
                  <RotateCcw className="h-4 w-4" />
                  New Remake
                </button>
              )}
            </div>
          </div>

          {/* Progress Card */}
          {taskStatus && (
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                {getStatusIcon(taskStatus.status)}
                <div>
                  <h3 className="text-sm font-semibold text-white">Processing Status</h3>
                  <p className={`text-xs font-medium capitalize ${getStatusColor(taskStatus.status)}`}>
                    {taskStatus.status}
                  </p>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mb-3">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
                  <span>Progress</span>
                  <span>{taskStatus.progress}%</span>
                </div>
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-purple-500 to-pink-500"
                    style={{ width: `${taskStatus.progress}%` }}
                  />
                </div>
              </div>

              {/* Task ID */}
              <p className="text-[10px] text-slate-600 font-mono break-all">
                ID: {taskStatus.task_id}
              </p>

              {/* Error Message */}
              {taskStatus.status === 'failed' && taskStatus.error_message && (
                <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                  <p className="text-xs text-red-400">{taskStatus.error_message}</p>
                </div>
              )}

              {/* Completed - Show Output */}
              {taskStatus.status === 'completed' && taskStatus.output_data?.video_url && (
                <div className="mt-4 space-y-3">
                  <div className="rounded-xl overflow-hidden bg-black/50 border border-green-500/20">
                    <video
                      src={taskStatus.output_data.video_url}
                      controls
                      className="w-full max-h-40 object-contain"
                    />
                  </div>
                  <a
                    href={taskStatus.output_data.video_url}
                    download
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm font-medium hover:bg-green-500/20 transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    Download Video
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
