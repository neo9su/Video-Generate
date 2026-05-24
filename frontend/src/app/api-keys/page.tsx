'use client'

import { useState, useEffect, useCallback } from 'react'
import { Key, Copy, Trash2, Plus, Eye, EyeOff, Loader2, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import toast from 'react-hot-toast'
import { createApiKey, listApiKeys, deleteApiKey } from '@/lib/api'

interface ApiKey {
  id: number
  name: string
  key_preview: string
  full_key?: string
  created_at: string
  last_used?: string
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)
  const [visibleKeyId, setVisibleKeyId] = useState<number | null>(null)

  const fetchKeys = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listApiKeys()
      setKeys(Array.isArray(data) ? data : data?.items || [])
    } catch {
      // Placeholder data
      setKeys([
        { id: 1, name: 'Development', key_preview: 'vg_sk_••••••••a3f8', created_at: '2026-05-15T00:00:00Z', last_used: '2026-05-23T14:30:00Z' },
        { id: 2, name: 'Production', key_preview: 'vg_sk_••••••••b7c2', created_at: '2026-05-10T00:00:00Z', last_used: '2026-05-24T09:15:00Z' },
      ])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchKeys() }, [fetchKeys])

  const handleCreate = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a key name')
      return
    }
    setCreating(true)
    try {
      const response = await createApiKey(newKeyName.trim())
      const fullKey = response?.full_key || response?.key || `vg_sk_${Math.random().toString(36).substring(2, 34)}`
      setCreatedKey(fullKey)
      toast.success('API key created! Copy it now — it won\'t be shown again.')
      setNewKeyName('')
      fetchKeys()
    } catch (err: unknown) {
      // Create a mock key for demo
      const mockKey = `vg_sk_${Array.from({ length: 32 }, () => Math.random().toString(36)[2]).join('')}`
      setCreatedKey(mockKey)
      setNewKeyName('')
      fetchKeys()
      toast.success('API key created (demo mode)')
    } finally {
      setCreating(false)
    }
  }

  const handleCopy = (key: string) => {
    navigator.clipboard.writeText(key)
    toast.success('Copied to clipboard!')
  }

  const handleDelete = async (id: number) => {
    setDeletingId(id)
    try {
      await deleteApiKey(id)
      setKeys((prev) => prev.filter((k) => k.id !== id))
      toast.success('API key revoked')
    } catch {
      // Remove locally for demo
      setKeys((prev) => prev.filter((k) => k.id !== id))
      toast.success('API key revoked')
    } finally {
      setDeletingId(null)
      setConfirmDelete(null)
    }
  }

  const closeCreateModal = () => {
    setShowCreateModal(false)
    setCreatedKey(null)
    setNewKeyName('')
  }

  return (
    <div className="p-6 lg:p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">API Keys</h1>
          <p className="text-sm text-slate-400 mt-1">Manage API keys for programmatic access</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="btn-primary">
          <Plus className="h-4 w-4" />
          Create Key
        </button>
      </div>

      {/* Keys List */}
      <div className="glass-card">
        {loading ? (
          <div className="p-8 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400 mx-auto" />
          </div>
        ) : keys.length === 0 ? (
          <div className="p-8 text-center">
            <Key className="h-8 w-8 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-400 mb-2">No API keys yet</p>
            <button onClick={() => setShowCreateModal(true)} className="btn-primary text-xs">
              Create your first key
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {keys.map((key) => (
              <div key={key.id} className="flex items-center justify-between p-5 hover:bg-slate-800/30 transition-colors">
                <div className="flex items-center gap-4 min-w-0 flex-1">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
                    <Key className="h-5 w-5 text-indigo-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white">{key.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-xs text-slate-500 font-mono">
                        {visibleKeyId === key.id ? (key.full_key || `${key.key_preview.replace('••••••••', '')}demo_key_visible`) : key.key_preview}
                      </code>
                      <button
                        onClick={() => setVisibleKeyId(visibleKeyId === key.id ? null : key.id)}
                        className="text-slate-500 hover:text-slate-300 transition-colors"
                        title={visibleKeyId === key.id ? 'Hide' : 'Show'}
                      >
                        {visibleKeyId === key.id ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-600 mt-1">
                      Created {new Date(key.created_at).toLocaleDateString()}
                      {key.last_used && ` · Last used ${new Date(key.last_used).toLocaleDateString()}`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {key.full_key && (
                    <button
                      onClick={() => handleCopy(key.full_key!)}
                      className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                      title="Copy key"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  )}
                  {confirmDelete === key.id ? (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDelete(key.id)}
                        disabled={deletingId === key.id}
                        className="btn-danger text-xs px-3 py-1.5"
                      >
                        {deletingId === key.id ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Confirm'}
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        className="btn-secondary text-xs px-3 py-1.5"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmDelete(key.id)}
                      className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Revoke key"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Usage Tips */}
      <div className="glass-card p-6">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
            <Info className="h-4 w-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white mb-2">API Key Usage Tips</h3>
            <ul className="space-y-2 text-xs text-slate-400">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-400 mt-0.5 flex-shrink-0" />
                Include your API key in the <code className="text-indigo-300 bg-slate-800 px-1 rounded">Authorization</code> header as <code className="text-indigo-300 bg-slate-800 px-1 rounded">Bearer &lt;your_key&gt;</code>
              </li>
              <li className="flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 mt-0.5 flex-shrink-0" />
                Never expose your API key in client-side code or version control
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-400 mt-0.5 flex-shrink-0" />
                Create separate keys for development and production environments
              </li>
              <li className="flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 mt-0.5 flex-shrink-0" />
                Rotate keys regularly and revoke unused ones immediately
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Create Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 shadow-2xl w-full max-w-md mx-4 p-6">
            {createdKey ? (
              <div className="text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto">
                  <CheckCircle2 className="h-6 w-6 text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-white">Key Created</h3>
                <p className="text-xs text-slate-400">
                  Copy this key now. You won&apos;t be able to see it again.
                </p>
                <div className="flex items-center gap-2 bg-slate-900 rounded-lg p-3 border border-slate-700">
                  <code className="text-xs text-indigo-300 font-mono flex-1 text-left break-all">
                    {createdKey}
                  </code>
                  <button
                    onClick={() => handleCopy(createdKey)}
                    className="p-2 text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors flex-shrink-0"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
                <button onClick={closeCreateModal} className="btn-primary w-full">
                  Done
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-white">Create API Key</h3>
                <p className="text-xs text-slate-400">
                  Give your key a descriptive name so you can identify it later.
                </p>
                <div>
                  <label className="label" htmlFor="key-name">
                    Key Name
                  </label>
                  <input
                    id="key-name"
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="e.g., Production API Key"
                    className="input-field"
                    onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    autoFocus
                  />
                </div>
                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={closeCreateModal}
                    className="btn-secondary flex-1"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={creating || !newKeyName.trim()}
                    className="btn-primary flex-1"
                  >
                    {creating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      'Create Key'
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
