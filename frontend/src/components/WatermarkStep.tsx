'use client'
import { useState, useRef, useEffect } from 'react'
import { Target, Move, ImageIcon, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'

interface BBox { x: number; y: number; w: number; h: number }
interface FrameAnnotation {
  frameUrl: string; bbox: BBox | null; timestamp?: number; segmentId?: number
}

export default function WatermarkStep({ videoPath, apiBaseUrl, onDone }: {
  videoPath: string; apiBaseUrl: string
  onDone: (data: { type: 'fixed' | 'moving'; frames: FrameAnnotation[]; description?: string }) => void
}) {
  const [step, setStep] = useState<'select' | 'loading' | 'annotate' | 'done'>('select')
  const [wmType, setWmType] = useState<'fixed' | 'moving' | null>(null)
  const [frames, setFrames] = useState<FrameAnnotation[]>([])
  const [desc, setDesc] = useState('')
  const [error, setError] = useState('')
  const loadFixed = async () => {
    setStep('loading'); setWmType('fixed'); setError('')
    try {
      const r = await fetch(`${apiBaseUrl}/watermark/frames`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, task_id: '' }),
      })
      if (!r.ok) throw Error('Extract failed')
      const d = await r.json()
      setFrames([
        { frameUrl: d.first_frame_url, bbox: null, timestamp: d.first_frame_ts },
        { frameUrl: d.last_frame_url, bbox: null, timestamp: d.last_frame_ts },
      ])
      setStep('annotate')
    } catch (e: any) { setError(e.message); setStep('select') }
  }
  const loadMoving = async () => {
    setStep('loading'); setWmType('moving'); setError('')
    try {
      const sr = await fetch(`${apiBaseUrl}/watermark/segments`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, threshold: 0.3 }),
      })
      if (!sr.ok) throw Error('Segments failed')
      const segs = (await sr.json()).segments || []
      const fr = await fetch(`${apiBaseUrl}/watermark/segment-frames`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, segments: segs, task_id: '' }),
      })
      if (!fr.ok) throw Error('Segment frames failed')
      const fd = await fr.json()
      setFrames((fd.frames || []).map((f: any) => ({
        frameUrl: f.first_frame_url, bbox: null, timestamp: f.start_time, segmentId: f.segment_id,
      })))
      setStep('annotate')
    } catch (e: any) { setError(e.message); setStep('select') }
  }
  const updateBbox = (idx: number, b: BBox) => {
    setFrames(p => p.map((f, i) => i === idx ? { ...f, bbox: b } : f))
  }
  const confirm = () => {
    if (!frames.some(f => f.bbox && f.bbox.w > 0)) {
      setError('Please mark watermark on at least one frame'); return
    }
    onDone({ type: wmType!, frames, description: desc || undefined })
    setStep('done')
  }
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-500/10">
          <Target className="h-4 w-4 text-red-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Watermark Removal</h3>
          <p className="text-xs text-slate-400">Mark watermark positions for removal</p>
        </div>
      </div>

      {step === 'select' && (
        <div className="grid grid-cols-2 gap-4">
          <button onClick={loadFixed} className="border-2 border-dashed border-slate-700 rounded-xl p-6 flex flex-col items-center gap-3 hover:border-red-500/50 transition-all">
            <Move className="h-10 w-10 text-red-400" />
            <span className="text-sm font-semibold text-slate-200">Fixed</span>
            <span className="text-[10px] text-slate-500">Watermark stays in one position</span>
          </button>
          <button onClick={loadMoving} className="border-2 border-dashed border-slate-700 rounded-xl p-6 flex flex-col items-center gap-3 hover:border-red-500/50 transition-all">
            <ImageIcon className="h-10 w-10 text-red-400" />
            <span className="text-sm font-semibold text-slate-200">Moving</span>
            <span className="text-[10px] text-slate-500">Watermark moves across video</span>
          </button>
        </div>
      )}

      {step === 'loading' && (
        <div className="flex items-center justify-center py-10 gap-3">
          <Loader2 className="h-6 w-6 text-red-400 animate-spin" />
          <span className="text-sm text-slate-400">Analyzing video...</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 mt-3">
          <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}
    </div>
  )
}

function FrameCanvas({ frameUrl, bbox, onBbox, label }: {
  frameUrl: string; bbox: BBox | null; onBbox: (b: BBox) => void; label: string
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  const [drawing, setDrawing] = useState(false)
  const [start, setStart] = useState({ x: 0, y: 0 })
  const scaleRef = useRef(1)

  useEffect(() => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const c = ref.current; if (!c) return
      const s = Math.min(400 / img.width, 300 / img.height, 1)
      scaleRef.current = s
      c.width = img.width * s; c.height = img.height * s
      const ctx = c.getContext('2d'); if (!ctx) return
      ctx.drawImage(img, 0, 0, c.width, c.height)
      if (bbox && bbox.w > 0) {
        ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2
        ctx.strokeRect(bbox.x * s, bbox.y * s, bbox.w * s, bbox.h * s)
        ctx.fillStyle = 'rgba(239,68,68,0.2)'
        ctx.fillRect(bbox.x * s, bbox.y * s, bbox.w * s, bbox.h * s)
      }
    }
    img.src = frameUrl
  }, [frameUrl, bbox])

  const onMouseDown = (e: React.MouseEvent) => {
    const r = ref.current?.getBoundingClientRect(); if (!r) return
    setStart({ x: e.clientX - r.left, y: e.clientY - r.top })
    setDrawing(true)
  }
  const onMouseMove = (e: React.MouseEvent) => {
    if (!drawing || !ref.current) return
    const r = ref.current.getBoundingClientRect(); const s = scaleRef.current
    const x = Math.min(start.x, e.clientX - r.left) / s
    const y = Math.min(start.y, e.clientY - r.top) / s
    const w = Math.abs(e.clientX - r.left - start.x) / s
    const h = Math.abs(e.clientY - r.top - start.y) / s
    onBbox({ x, y, w, h })
  }
  const onMouseUp = () => setDrawing(false)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">{label}</span>
        {bbox && bbox.w > 0 && (
          <button onClick={() => onBbox({ x: 0, y: 0, w: 0, h: 0 })}
            className="text-[10px] text-red-400 hover:text-red-300">Clear</button>
        )}
      </div>
      <canvas ref={ref} onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp}
        className="border border-slate-700 rounded-lg cursor-crosshair w-full max-w-[400px]"
        style={{ maxHeight: 300 }} />
      {bbox && bbox.w > 0 && (
        <p className="text-[10px] text-slate-500 font-mono">
          [{Math.round(bbox.x)},{Math.round(bbox.y)} {Math.round(bbox.w)}x{Math.round(bbox.h)}]
        </p>
      )}
    </div>
  )
}
