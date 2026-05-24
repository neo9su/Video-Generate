'use client'

import { useState, useEffect } from 'react'
import { CreditCard, Download, History, Loader2, Coins, ArrowUpRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { purchaseCredits, getTransactions, getPlans, subscribe } from '@/lib/api'

const creditPackages = [
  { amount: 100, price: '$10', bonus: null },
  { amount: 500, price: '$45', bonus: '50 free' },
  { amount: 1000, price: '$80', bonus: '150 free' },
  { amount: 5000, price: '$350', bonus: '1000 free' },
]

interface Transaction {
  id: number
  type: string
  amount: number
  credits: number
  status: string
  created_at: string
}

export default function BillingPage() {
  const [currentPlan, setCurrentPlan] = useState<string>('Free')
  const [credits, setCredits] = useState<number>(150)
  const [creditsUsed, setCreditsUsed] = useState<number>(23)
  const [purchasing, setPurchasing] = useState<number | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBillingData()
  }, [])

  const loadBillingData = async () => {
    try {
      setLoading(true)
      const [txData] = await Promise.all([
        getTransactions().catch(() => []),
      ])
      setTransactions(Array.isArray(txData) ? txData : [])
    } catch {
      // Use placeholder data
      setTransactions([
        { id: 1, type: 'credit_purchase', amount: 10, credits: 500, status: 'completed', created_at: '2026-05-20T10:30:00Z' },
        { id: 2, type: 'subscription', amount: 29, credits: 0, status: 'completed', created_at: '2026-05-01T00:00:00Z' },
        { id: 3, type: 'credit_usage', amount: 0, credits: -50, status: 'completed', created_at: '2026-05-18T14:22:00Z' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handlePurchase = async (amount: number) => {
    setPurchasing(amount)
    try {
      await purchaseCredits(amount)
      setCredits((prev) => prev + amount)
      toast.success(`Purchased ${amount} credits!`)
      loadBillingData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Purchase failed')
    } finally {
      setPurchasing(null)
    }
  }

  const handleUpgrade = async () => {
    try {
      await subscribe('pro')
      setCurrentPlan('Pro')
      toast.success('Upgraded to Pro plan!')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Upgrade failed')
    }
  }

  const maxCredits = currentPlan === 'Free' ? 500 : currentPlan === 'Pro' ? 5000 : 50000
  const creditsPercent = Math.min((credits / maxCredits) * 100, 100)
  const usagePercent = creditsUsed > 0 ? Math.min((creditsUsed / (credits + creditsUsed)) * 100, 100) : 0

  return (
    <div className="p-6 lg:p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Billing</h1>
        <p className="text-sm text-slate-400 mt-1">Manage your subscription and credits</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Current Plan */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <CreditCard className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">Current Plan</p>
              <p className="text-lg font-bold text-white">{currentPlan}</p>
            </div>
          </div>
          {currentPlan === 'Free' ? (
            <button onClick={handleUpgrade} className="btn-primary w-full">
              <ArrowUpRight className="h-4 w-4" />
              Upgrade to Pro
            </button>
          ) : (
            <div className="flex items-center gap-2 text-sm text-green-400">
              <span className="w-2 h-2 rounded-full bg-green-400" />
              Active
            </div>
          )}
        </div>

        {/* Credit Balance */}
        <div className="glass-card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Coins className="h-5 w-5 text-yellow-400" />
              <h2 className="text-base font-semibold text-white">Credit Balance</h2>
            </div>
            <span className="text-2xl font-bold text-white">{credits.toLocaleString()}</span>
          </div>

          {/* Usage bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Usage this month</span>
              <span>{creditsUsed} credits used</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
                style={{ width: `${usagePercent}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Remaining: {credits.toLocaleString()} / {maxCredits.toLocaleString()}</span>
              <span>{Math.round(creditsPercent)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Purchase Credits */}
      <div className="glass-card p-6">
        <h2 className="text-base font-semibold text-white mb-4">Purchase Credits</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {creditPackages.map((pkg) => (
            <button
              key={pkg.amount}
              onClick={() => handlePurchase(pkg.amount)}
              disabled={purchasing !== null}
              className="glass-card-hover p-4 text-center border border-slate-700/50 rounded-xl"
            >
              <p className="text-lg font-bold text-white">{pkg.amount.toLocaleString()}</p>
              <p className="text-xs text-slate-400 mt-1">credits</p>
              <p className="text-sm font-semibold text-indigo-400 mt-2">{pkg.price}</p>
              {pkg.bonus && (
                <p className="text-[10px] text-green-400 mt-1">+{pkg.bonus}</p>
              )}
              {purchasing === pkg.amount ? (
                <Loader2 className="h-4 w-4 animate-spin mx-auto mt-2 text-indigo-400" />
              ) : (
                <p className="text-xs text-slate-500 mt-2">Click to buy</p>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Transaction History */}
      <div className="glass-card">
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-slate-400" />
            <h2 className="text-base font-semibold text-white">Transaction History</h2>
          </div>
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400 mx-auto" />
            </div>
          ) : transactions.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500">No transactions yet</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left py-3 px-5 text-slate-500 font-medium">Date</th>
                  <th className="text-left py-3 px-5 text-slate-500 font-medium">Type</th>
                  <th className="text-right py-3 px-5 text-slate-500 font-medium">Amount</th>
                  <th className="text-right py-3 px-5 text-slate-500 font-medium">Credits</th>
                  <th className="text-center py-3 px-5 text-slate-500 font-medium">Status</th>
                  <th className="text-center py-3 px-5 text-slate-500 font-medium">Invoice</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                    <td className="py-3 px-5 text-slate-300">
                      {new Date(tx.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-5">
                      <span className="capitalize text-slate-300">
                        {tx.type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-5 text-right text-slate-300">
                      {tx.amount > 0 ? `$${tx.amount}` : '—'}
                    </td>
                    <td className={`py-3 px-5 text-right font-medium ${
                      tx.credits > 0 ? 'text-green-400' : tx.credits < 0 ? 'text-red-400' : 'text-slate-500'
                    }`}>
                      {tx.credits > 0 ? `+${tx.credits}` : tx.credits < 0 ? tx.credits : '—'}
                    </td>
                    <td className="py-3 px-5 text-center">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-green-400/10 text-green-400 border border-green-400/20">
                        {tx.status}
                      </span>
                    </td>
                    <td className="py-3 px-5 text-center">
                      <button
                        onClick={() => toast.success('Invoice download started (placeholder)')}
                        className="text-slate-500 hover:text-indigo-400 transition-colors"
                        title="Download invoice"
                      >
                        <Download className="h-4 w-4 mx-auto" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
