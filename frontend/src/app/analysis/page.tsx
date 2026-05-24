'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  Video,
  Upload,
  BarChart3,
  Palette,
  Film,
  Clock,
  Image,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  History,
  Play,
  Trash2,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { analyzeVideo, getAnalysis, type AnalysisResponse, type AnalysisResult } from '@/lib/api'

interface HistoryItem {
  id: string
  videoName: string
  result: AnalysisResult
  timestamp: Date
}

export default function AnalysisPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [activeTab, setActiveTab] = useState<'style' | 'pacing' | 'scenes' | 'colors'>('style')
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [showHistory, setShowHistory] = useState(false)

  // Load history from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem('analysis_history')
      if (saved) {
        const parsed = JSON.parse(saved)
        setHistory(parsed.map((item: HistoryItem) => ({
          ...item,
          timestamp: new Date(item.timestamp),
        })))
      }
    } catch {
      // ignore
    }
  }, [])

  const saveToHistory = (id: string, videoName: string, result: AnalysisResult) => {
    const newItem: HistoryItem = { id, videoName, result, timestamp: new Date() }
    const updated = [newItem, ...history].slice(0, 20) // Keep last 20
    setHistory(updated)
    try {
      localStorage.setItem('analysis_history', JSON.stringify(updated))
    } catch {
      // ignore
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return

    setFile(selectedFile)
    setVideoUrl(URL.createObjectURL(selectedFile))
    setResult(null)
    setAnalyzing(true)

    try {
      const analysisResult = await analyzeVideo(selectedFile)
      setResult(analysisResult)
      saveToHistory(analysisResult.task_id, selectedFile.name, analysisResult.result)
      toast.success('Analysis complete!')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Analysis failed'
      toast.error(message)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleUseThisStyle = () => {
    if (!result) return
    // Navigate to create page with analysis ID in query params
    router.push(`/create?analysis_id=${result.task_id}`)
  }

  const clearHistory = () => {
    setHistory([])
    localStorage.removeItem('analysis_history')
    toast.success('History cleared')
  }

  const removeHistoryItem = (id: string) => {
    const updated = history.filter((h) => h.id !== id)
    setHistory(updated)
    try {
      localStorage.setItem('analysis_history', JSON.stringify(updated))
    } catch {
      // ignore
    }
  }

  const renderAnalysisContent = () => {
    if (!result?.result) return null
    const data = result.result

    switch (activeTab) {
      case 'style':
        return (
          <div className="grid gap-4">
            <div className="glass-card p-4 border-purple-500/20">
              <div className="flex items-center gap-2 mb-3">
                <Palette className="h-5 w-5 text-purple-400" />
                <h3 className="text-sm font-semibold text-slate-200">Visual Style Analysis</h3>
              </div>
              {data.style && Object.keys(data.style).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(data.style).map(([key, value]) => (
                    <div key={key} className="flex items-start gap-2">
                      <span className="text-xs font-medium text-purple-400 uppercase min-w-[100px]">{key}:</span>
                      <span className="text-sm text-slate-300">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No style data extracted</p>
              )}
            </div>
          </div>
        )

      case 'pacing':
        return (
          <div className="grid gap-4">
            <div className="glass-card p-4 border-blue-500/20">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="h-5 w-5 text-blue-400" />
                <h3 className="text-sm font-semibold text-slate-200">Pacing Analysis</h3>
              </div>
              {data.pacing && Object.keys(data.pacing).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(data.pacing).map(([key, value]) => (
                    <div key={key} className="flex items-start gap-2">
                      <span className="text-xs font-medium text-blue-400 uppercase min-w-[120px]">{key}:</span>
                      <span className="text-sm text-slate-300">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No pacing data extracted</p>
              )}
            </div>
          </div>
        )

      case 'scenes':
        return (
          <div className="grid gap-4">
            <div className="glass-card p-4 border-green-500/20">
              <div className="flex items-center gap-2 mb-3">
                <Film className="h-5 w-5 text-green-400" />
                <h3 className="text-sm font-semibold text-slate-200">
                  Scene Detection ({Array.isArray(data.scenes) ? data.scenes.length : 0} scenes)
                </h3>
              </div>
              {Array.isArray(data.scenes) && data.scenes.length > 0 ? (
                <div className="space-y-2">
                  {data.scenes.map((scene, i) => (
                    <div key={i} className="rounded-lg bg-slate-800/50 p-3 border border-slate-700">
                      <p className="text-xs font-medium text-green-400 mb-1">Scene {i + 1}</p>
                      {typeof scene === 'object' && Object.entries(scene).map(([key, value]) => (
                        <p key={key} className="text-xs text-slate-400">
                          <span className="text-slate-500 capitalize">{key}: </span>
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </p>
                      ))}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No scenes detected</p>
              )}
            </div>
          </div>
        )

      case 'colors':
        return (
          <div className="grid gap-4">
            <div className="glass-card p-4 border-yellow-500/20">
              <div className="flex items-center gap-2 mb-3">
                <Image className="h-5 w-5 text-yellow-400" />
                <h3 className="text-sm font-semibold text-slate-200">Color Palette</h3>
              </div>
              {data.colors && Object.keys(data.colors).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(data.colors).map(([key, value]) => (
                    <div key={key} className="flex items-start gap-2">
                      <span className="text-xs font-medium text-yellow-400 uppercase min-w-[120px]">{key}:</span>
                      <span className="text-sm text-slate-300">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No color data extracted</p>
              )}
            </div>
          </div>
        )
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto animate-fade-in">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <BarChart3 className="h-6 w-6 text-indigo-400" />
              Video Analysis
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Analyze reference videos to extract style, pacing, scenes, and color information.
            </p>
          </div>
          {history.length > 0 && (
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="btn-secondary text-sm"
            >
              <History className="h-4 w-4" />
              History ({history.length})
            </button>
          )}
        </div>
      </div>

      {/* History Panel */}
      {showHistory && history.length > 0 && (
        <div className="mb-8 glass-card p-4 border-indigo-500/20">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <History className="h-4 w-4 text-indigo-400" />
              Analysis History
            </h3>
            <button
              onClick={clearHistory}
              className="text-xs text-red-400 hover:text-red-300"
            >
              Clear All
            </button>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {history.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-lg bg-slate-800/50 p-3 border border-slate-700"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Video className="h-4 w-4 text-slate-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-300 truncate">{item.videoName}</p>
                    <p className="text-xs text-slate-500">
                      {item.timestamp.toLocaleDateString()} {item.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => {
                      setResult({ task_id: item.id, status: 'completed', result: item.result })
                      setShowHistory(false)
                      setActiveTab('style')
                      toast.success('Loaded analysis from history')
                    }}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-400 hover:bg-indigo-500/10"
                    title="Load analysis"
                  >
                    <Play className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => removeHistoryItem(item.id)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                    title="Remove"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Section */}
      <div className="glass-card p-8 mb-8">
        <div className="flex flex-col items-center justify-center gap-4">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-indigo-500/10">
            <Upload className="h-10 w-10 text-indigo-400" />
          </div>
          <div className="text-center">
            <h2 className="text-lg font-semibold text-white mb-1">Upload Reference Video</h2>
            <p className="text-sm text-slate-400">
              Upload a video to analyze its style, pacing, scenes, and color palette.
            </p>
          </div>

          <input
            type="file"
            accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
            onChange={handleFileChange}
            className="hidden"
            id="analysis-video-upload"
          />
          <label
            htmlFor="analysis-video-upload"
            className="flex items-center justify-center gap-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 px-6 py-3 text-sm font-medium hover:bg-indigo-500/20 transition-colors cursor-pointer"
          >
            <Upload className="h-4 w-4" />
            Select Video File
          </label>
        </div>
      </div>

      {/* Video Preview + Analysis */}
      {analyzing && (
        <div className="glass-card p-8 mb-8 border-purple-500/30">
          <div className="flex flex-col items-center justify-center gap-4">
            <Loader2 className="h-10 w-10 text-purple-400 animate-spin" />
            <div className="text-center">
              <p className="text-sm font-medium text-slate-200">Analyzing video...</p>
              <p className="text-xs text-slate-500 mt-1">
                Extracting style, pacing, scenes, and color information
              </p>
            </div>
            <div className="w-full max-w-xs h-2 rounded-full bg-slate-700 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 animate-pulse"
                style={{ width: '60%' }}
              />
            </div>
          </div>
        </div>
      )}

      {videoUrl && !analyzing && (
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Video Preview */}
          <div className="glass-card overflow-hidden">
            <video
              src={videoUrl}
              controls
              className="w-full bg-black"
            />
            <div className="p-3 flex items-center justify-between">
              <p className="text-sm text-slate-300 truncate">{file?.name}</p>
              <button
                onClick={() => {
                  setFile(null)
                  setVideoUrl(null)
                  setResult(null)
                }}
                className="text-xs text-red-400 hover:text-red-300"
              >
                Remove
              </button>
            </div>
          </div>

          {/* Analysis Results */}
          {result && (
            <div>
              {/* Tabs */}
              <div className="flex gap-1 mb-4 rounded-lg bg-slate-800 p-1">
                {(['style', 'pacing', 'scenes', 'colors'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-all ${
                      activeTab === tab
                        ? 'bg-indigo-500/20 text-indigo-400'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {tab === 'style' && <Palette className="h-3 w-3" />}
                    {tab === 'pacing' && <Clock className="h-3 w-3" />}
                    {tab === 'scenes' && <Film className="h-3 w-3" />}
                    {tab === 'colors' && <Image className="h-3 w-3" />}
                    <span className="capitalize">{tab}</span>
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="space-y-4 max-h-[400px] overflow-y-auto">
                {renderAnalysisContent()}

                {/* Use This Style Button */}
                <button
                  onClick={handleUseThisStyle}
                  className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 text-white px-4 py-3 text-sm font-medium hover:from-indigo-600 hover:to-purple-700 transition-colors"
                >
                  <Sparkles className="h-4 w-4" />
                  Use This Style in New Video
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state when no video */}
      {!videoUrl && !analyzing && (
        <div className="glass-card p-12 text-center">
          <BarChart3 className="h-16 w-16 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-400 font-medium text-lg">No video analyzed yet</p>
          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
            Upload a reference video above to analyze its visual style, pacing, scene transitions, and color palette. The AI will extract insights that can be applied to your generated videos.
          </p>
        </div>
      )}
    </div>
  )
}
