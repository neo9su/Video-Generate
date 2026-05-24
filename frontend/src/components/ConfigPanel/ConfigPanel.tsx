'use client'

import { useState } from 'react'
import { Settings2 } from 'lucide-react'

export interface ConfigValues {
  platform: string
  style: string
  language: string
  videoLength: number
  model: string
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

const models = [
  { value: 'standard', label: 'Standard', description: 'Fast, good quality' },
  { value: 'pro', label: 'Pro', description: 'High quality, longer render' },
  { value: 'premium', label: 'Premium', description: 'Best quality, longest render' },
]

export default function ConfigPanel({ values, onChange }: ConfigPanelProps) {
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

      {/* Style */}
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

      {/* Model */}
      <div>
        <label className="label">Generation Model</label>
        <div className="space-y-2">
          {models.map((m) => (
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
    </div>
  )
}
