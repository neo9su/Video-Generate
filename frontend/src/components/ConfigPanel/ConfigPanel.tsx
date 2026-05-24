'use client'

import { useState, useEffect } from 'react'
import { Settings2, Mic, Sparkles, Film } from 'lucide-react'
import { getVoices, type Voice } from '@/lib/api'

export interface ConfigValues {
  platform: string
  style: string
  language: string
  videoLength: number
  model: string
  highlightStyle: string
  voiceId: string
  useReferenceAnalysis: boolean
  referenceAnalysisId?: string
  comfyuiModel: string
}

interface ConfigPanelProps {
  values: ConfigValues
  onChange: (values: ConfigValues) => void
}

const platforms = [
  { value: 'tiktok', label: 'TikTok', description: '9:16 vertical short video' },
  { value: 'douyin', label: '抖音', description: '9:16 vertical short video' },
  { value: 'xiaohongshu', label: 'Xiaohongshu', description: '3:4 vertical video' },
  { value: 'instagram', label: 'Instagram', description: '1:1 square or 9:16' },
  { value: 'amazon', label: 'Amazon', description: '16:9 product video' },
  { value: 'shopify', label: 'Shopify', description: '16:9 product video' },
]

const styles = [
  { value: 'apple', label: 'Apple', description: 'Clean, minimalist, white space' },
  { value: 'tech', label: 'Tech', description: 'Modern, bold, gradient accents' },
  { value: 'premium', label: 'Premium', description: 'Luxury, dark, elegant' },
  { value: 'trendy', label: 'Trendy', description: 'Vibrant, social-media ready' },
  { value: 'minimal', label: 'Minimal', description: 'Simple, clean, no distractions' },
]

const languages = [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文 (Chinese)' },
  { value: 'ja', label: '日本語 (Japanese)' },
  { value: 'ko', label: '한국어 (Korean)' },
  { value: 'es', label: 'Español' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
]

const highlightStyles = [
  { value: 'tiktok', label: 'TikTok', description: 'Bold, animated, colorful highlights' },
  { value: 'dynamic', label: 'Dynamic', description: 'Energetic scale/color animations' },
  { value: 'classic', label: 'Classic', description: 'Clean underline and bold' },
  { value: 'minimal', label: 'Minimal', description: 'Subtle, modern, no distractions' },
]

const comfyuiModels = [
  { value: 'sd3.5', label: 'SD 3.5', description: 'Stable Diffusion 3.5 — best quality' },
  { value: 'sdxl', label: 'SDXL', description: 'Stable Diffusion XL — high quality' },
  { value: 'flux', label: 'Flux', description: 'Flux — fastest generation' },
]

const generationModels = [
  { value: 'standard', label: 'Standard', description: 'Fast, good quality' },
  { value: 'pro', label: 'Pro', description: 'High quality, longer render' },
  { value: 'premium', label: 'Premium', description: 'Best quality, longest render' },
]

export default function ConfigPanel({ values, onChange }: ConfigPanelProps) {
  const [voices, setVoices] = useState<Voice[]>([])
  const [loadingVoices, setLoadingVoices] = useState(false)

  useEffect(() => {
    const fetchVoices = async () => {
      setLoadingVoices(true)
      try {
        const data = await getVoices()
        setVoices(data)
      } catch {
        // Silently fail — voice selector will show "No voices available"
      } finally {
        setLoadingVoices(false)
      }
    }
    fetchVoices()
  }, [])

  const update = (partial: Partial<ConfigValues>) => {
    onChange({ ...values, ...partial })
  }

  return (
    <div className="space-y-6">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <Settings2 className="h-5 w-5 text-indigo-400" />
        <h3 className="text-sm font-semibold text-slate-200">Video Configuration</h3>
      </div>

      {/* Platform */}
      <div>
        <label className="label">Platform</label>
        <div className="grid grid-cols-2 gap-2">
          {platforms.map((p) => (
            <button
              key={p.value}
              onClick={() => update({ platform: p.value })}
              className={`text-left rounded-lg border p-3 transition-all duration-200 ${
                values.platform === p.value
                  ? 'border-indigo-500 bg-indigo-500/10 ring-1 ring-indigo-500'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800'
              }`}
            >
              <p className="text-sm font-medium text-slate-200">{p.label}</p>
              <p className="text-xs text-slate-500 mt-0.5">{p.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Visual Style */}
      <div>
        <label className="label">Visual Style</label>
        <div className="grid grid-cols-2 gap-2">
          {styles.map((s) => (
            <button
              key={s.value}
              onClick={() => update({ style: s.value })}
              className={`text-left rounded-lg border p-3 transition-all duration-200 ${
                values.style === s.value
                  ? 'border-indigo-500 bg-indigo-500/10 ring-1 ring-indigo-500'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800'
              }`}
            >
              <p className="text-sm font-medium text-slate-200">{s.label}</p>
              <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Highlight Style — NEW */}
      <div>
        <label className="label flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-yellow-400" />
          Highlight Style
        </label>
        <div className="grid grid-cols-2 gap-2">
          {highlightStyles.map((hs) => (
            <button
              key={hs.value}
              onClick={() => update({ highlightStyle: hs.value })}
              className={`text-left rounded-lg border p-3 transition-all duration-200 ${
                values.highlightStyle === hs.value
                  ? 'border-yellow-500 bg-yellow-500/10 ring-1 ring-yellow-500'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800'
              }`}
            >
              <p className="text-sm font-medium text-slate-200">{hs.label}</p>
              <p className="text-xs text-slate-500 mt-0.5">{hs.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Language */}
      <div>
        <label className="label" htmlFor="language">Language</label>
        <select
          id="language"
          value={values.language}
          onChange={(e) => update({ language: e.target.value })}
          className="select-field"
        >
          {languages.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {/* Video Length */}
      <div>
        <label className="label">
          Video Length: <span className="text-indigo-400">{values.videoLength}s</span>
        </label>
        <input
          type="range"
          min={15}
          max={120}
          step={5}
          value={values.videoLength}
          onChange={(e) => update({ videoLength: parseInt(e.target.value) })}
          className="w-full h-2 rounded-full appearance-none cursor-pointer bg-slate-700 accent-indigo-500"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>15s</span>
          <span>60s</span>
          <span>120s</span>
        </div>
      </div>

      {/* Voice Selector — NEW */}
      <div>
        <label className="label flex items-center gap-2">
          <Mic className="h-4 w-4 text-indigo-400" />
          Narration Voice
        </label>
        <select
          value={values.voiceId}
          onChange={(e) => update({ voiceId: e.target.value })}
          className="select-field"
        >
          <option value="">Default (System Voice)</option>
          {loadingVoices ? (
            <option value="" disabled>Loading voices...</option>
          ) : voices.length === 0 ? (
            <option value="" disabled>No cloned voices — add one in Voices</option>
          ) : (
            voices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} {v.is_default ? '(Default)' : ''}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Reference Analysis Toggle — NEW */}
      <div>
        <label className="label flex items-center gap-2">
          <Film className="h-4 w-4 text-purple-400" />
          Reference Video Analysis
        </label>
        <div className="flex items-center gap-3">
          <button
            onClick={() => update({ useReferenceAnalysis: !values.useReferenceAnalysis })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              values.useReferenceAnalysis ? 'bg-indigo-500' : 'bg-slate-700'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                values.useReferenceAnalysis ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
          <span className="text-sm text-slate-400">
            {values.useReferenceAnalysis
              ? 'Style analysis will be applied from reference video'
              : 'Use manual style selection instead'}
          </span>
        </div>
        {values.referenceAnalysisId && (
          <p className="text-xs text-green-400 mt-1">
            ✓ Analysis ID: {values.referenceAnalysisId}
          </p>
        )}
      </div>

      {/* Generation Model */}
      <div>
        <label className="label">Generation Model</label>
        <div className="space-y-2">
          {generationModels.map((m) => (
            <button
              key={m.value}
              onClick={() => update({ model: m.value })}
              className={`w-full text-left rounded-lg border p-3 transition-all duration-200 ${
                values.model === m.value
                  ? 'border-indigo-500 bg-indigo-500/10 ring-1 ring-indigo-500'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-slate-200">{m.label}</p>
                <span
                  className={`text-xs ${
                    m.value === 'premium'
                      ? 'text-purple-400'
                      : m.value === 'pro'
                      ? 'text-indigo-400'
                      : 'text-slate-400'
                  }`}
                >
                  {m.value === 'premium' ? '✦ Best' : m.value === 'pro' ? '●' : '○'}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{m.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* ComfyUI Model Selector — NEW */}
      <div>
        <label className="label">ComfyUI Image Model</label>
        <div className="grid grid-cols-3 gap-2">
          {comfyuiModels.map((cm) => (
            <button
              key={cm.value}
              onClick={() => update({ comfyuiModel: cm.value })}
              className={`text-center rounded-lg border p-2 transition-all duration-200 ${
                values.comfyuiModel === cm.value
                  ? 'border-purple-500 bg-purple-500/10 ring-1 ring-purple-500'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800'
              }`}
            >
              <p className="text-xs font-medium text-slate-200">{cm.label}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">{cm.description}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
