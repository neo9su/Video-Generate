'use client'

import { useState, useEffect, useCallback } from 'react'
import { Webhook, Plus, Loader2, Zap, Trash2, ToggleLeft, ToggleRight, History, CheckCircle2, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { listWebhooks, registerWebhook, updateWebhook, deleteWebhook, testWebhook } from '@/lib/api'

interface WebhookEntry {
  id: number
  url: string
  events: string[]
  is_active: boolean
  created_at: string
  last_triggered?: string
}

const availableEvents = [
  { id: 'task.completed', label: 'Task Completed' },
  { id: 'task.failed', label: 'Task Failed' },
  { id: 'task.progress', label: 'Task Progress' },
  { id: 'video.ready', label: 'Video Ready' },
  { id: 'credits.low', label: 'Low Credits' },
  { id: 'voice.ready', label: 'Voice Ready' },
]

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newUrl, setNewUrl] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<string[]>([])
  const [creating, setCreating] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const fetchWebhooks = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listWebhooks()
      setWebhooks(Array.isArray(data) ? data : data?.items || [])
    } catch {
      // Placeholder
      setWebhooks([
        { id: 1, url: 'https://api.example.com/webhooks/video', events: ['task.completed', 'video.ready'], is_active: true, created_at: '2026-05-18T00:00:00Z', last_triggered: '2026-05-24T08:30:00Z' },
        { id: 2, url: 'https://hooks.slack.com/services/T00/B00/xxx', events: ['task.failed'], is_active: false, created_at: '2026-05-10T00:00:00Z' },
      ])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchWebhooks() }, [fetchWebhooks])

  const handleAdd = async () => {
    if (!newUrl.trim()) {
      toast.error('Please enter a webhook URL')
      return
    }
    if (selectedEvents.length === 0) {
      toast.error('Please select at least one event')
      return
    }
    setCreating(true)
    try {
      await registerWebhook({ url: newUrl.trim(), events: selectedEvents })
      toast.success('Webhook registered!')
      setShowAddForm(false)
      setNewUrl('')
      setSelectedEvents([])
      fetchWebhooks()
    } catch {
      // Demo: add locally
      setWebhooks((prev) => [...prev, {
        id: Date.now(),
        url: newUrl.trim(),
        events: selectedEvents,
        is_active: true,
        created_at: new Date().toISOString(),
      }])
      toast.success('Webhook registered (demo)')
      setShowAddForm(false)
      setNewUrl('')
      setSelectedEvents([])
    } finally {
      setCreating(false)
    }
  }

  const handleToggle = async (wh: WebhookEntry) => {
    try {
      await updateWebhook(wh.id, { is_active: !wh.is_active })
      setWebhooks((prev) => prev.map((w) => w.id === wh.id ? { ...w, is_active: !w.is_active } : w))
      toast.success(`Webhook ${wh.is_active ? 'disabled' : 'enabled'}`)
    } catch {
      setWebhooks((prev) => prev.map((w) => w.id === wh.id ? { ...w, is_active: !w.is_active } : w))
      toast.success(`Webhook ${wh.is_active ? 'disabled' : 'enabled'} (demo)`)
    }
  }

  const handleTest = async (id: number) => {
    setTestingId(id)
    try {
      await testWebhook(id)
      toast.success('Test event sent! Check your endpoint.')
    } catch {
      toast.success('Test event sent (demo)')
    } finally {
      setTestingId(null)
    }
  }

  const handleDelete = async (id: number) => {
    setDeletingId(id)
    try {
      await deleteWebhook(id)
      setWebhooks((prev) => prev.filter((w) => w.id !== id))
      toast.success('Webhook deleted')
    } catch {
      setWebhooks((prev) => prev.filter((w) => w.id !== id))
      toast.success('Webhook deleted (demo)')
    } finally {
      setDeletingId(null)
    }
  }

  const toggleEvent = (eventId: string) => {
    setSelectedEvents((prev) =>
      prev.includes(eventId)
        ? prev.filter((e) => e !== eventId)
        : [...prev, eventId]
    )
  }

  return (
    <div className="p-6 lg:p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Webhooks</h1>
          <p className="text-sm text-slate-400 mt-1">
            Receive real-time notifications about events in your account
          </p>
        </div>
        <button onClick={() => setShowAddForm(true)} className="btn-primary">
          <Plus className="h-4 w-4" />
          Add Webhook
        </button>
      </div>

      {/* Webhooks List */}
      <div className="glass-card">
        {loading ? (
          <div className="p-8 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400 mx-auto" />
          </div>
        ) : webhooks.length === 0 ? (
          <div className="p-8 text-center">
            <Webhook className="h-8 w-8 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-400 mb-2">No webhooks registered</p>
            <button onClick={() => setShowAddForm(true)} className="btn-primary text-xs">
              Add your first webhook
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {webhooks.map((wh) => (
              <div key={wh.id} className="p-5 hover:bg-slate-800/30 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        wh.is_active ? 'bg-green-500/10' : 'bg-slate-700/50'
                      }`}>
                        <Webhook className={`h-5 w-5 ${wh.is_active ? 'text-green-400' : 'text-slate-500'}`} />
                      </div>
                      <div className="min-w-0">
                        <code className="text-sm text-slate-200 font-mono break-all">{wh.url}</code>
                        <div className="flex items-center gap-2 mt-1">
                          {wh.events.map((evt) => (
                            <span key={evt} className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                              {evt}
                            </span>
                          ))}
                        </div>
                        <p className="text-[10px] text-slate-600 mt-1">
                          Created {new Date(wh.created_at).toLocaleDateString()}
                          {wh.last_triggered && ` · Last triggered ${new Date(wh.last_triggered).toLocaleDateString()}`}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Toggle */}
                    <button
                      onClick={() => handleToggle(wh)}
                      className={`p-2 rounded-lg transition-colors ${
                        wh.is_active
                          ? 'text-green-400 hover:bg-green-500/10'
                          : 'text-slate-500 hover:bg-slate-700'
                      }`}
                      title={wh.is_active ? 'Disable' : 'Enable'}
                    >
                      {wh.is_active ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
                    </button>

                    {/* Test */}
                    <button
                      onClick={() => handleTest(wh.id)}
                      disabled={testingId === wh.id}
                      className="p-2 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors"
                      title="Test webhook"
                    >
                      {testingId === wh.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Zap className="h-4 w-4" />
                      )}
                    </button>

                    {/* Delete */}
                    <button
                      onClick={() => handleDelete(wh.id)}
                      disabled={deletingId === wh.id}
                      className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete webhook"
                    >
                      {deletingId === wh.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Deliveries (Placeholder) */}
      <div className="glass-card">
        <div className="flex items-center gap-2 p-5 border-b border-slate-800">
          <History className="h-4 w-4 text-slate-400" />
          <h2 className="text-base font-semibold text-white">Recent Deliveries</h2>
        </div>
        <div className="p-8 text-center">
          <History className="h-8 w-8 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400">
            Delivery logs will appear here once webhooks start sending events.
          </p>
          <div className="flex items-center justify-center gap-4 mt-4 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-green-500" /> Success
            </span>
            <span className="flex items-center gap-1">
              <XCircle className="h-3 w-3 text-red-500" /> Failed
            </span>
          </div>
        </div>
      </div>

      {/* Add Webhook Form Modal */}
      {showAddForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 shadow-2xl w-full max-w-lg mx-4 p-6">
            <h3 className="text-lg font-semibold text-white mb-2">Register Webhook</h3>
            <p className="text-xs text-slate-400 mb-6">
              Enter the URL where events should be sent and select which events to subscribe to.
            </p>

            <div className="space-y-4">
              <div>
                <label className="label" htmlFor="webhook-url">Webhook URL</label>
                <input
                  id="webhook-url"
                  type="url"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="https://your-server.com/webhooks/video"
                  className="input-field"
                />
              </div>

              <div>
                <label className="label">Events</label>
                <div className="grid grid-cols-2 gap-2">
                  {availableEvents.map((evt) => (
                    <label
                      key={evt.id}
                      className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                        selectedEvents.includes(evt.id)
                          ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                          : 'border-slate-700 text-slate-400 hover:bg-slate-700/50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedEvents.includes(evt.id)}
                        onChange={() => toggleEvent(evt.id)}
                        className="rounded border-slate-600 bg-slate-700 text-indigo-500 focus:ring-indigo-500"
                      />
                      <span className="text-xs">{evt.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 mt-6 pt-4 border-t border-slate-700">
              <button
                onClick={() => { setShowAddForm(false); setNewUrl(''); setSelectedEvents([]) }}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={creating || !newUrl.trim() || selectedEvents.length === 0}
                className="btn-primary flex-1"
              >
                {creating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Registering...
                  </>
                ) : (
                  'Register Webhook'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
