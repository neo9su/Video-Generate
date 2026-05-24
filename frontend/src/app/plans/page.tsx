'use client'

import { useState } from 'react'
import { Check, X, Loader2, Sparkles, Zap, Shield } from 'lucide-react'
import toast from 'react-hot-toast'
import { subscribe } from '@/lib/api'

const plans = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'Perfect for getting started',
    icon: Sparkles,
    color: 'from-slate-400 to-slate-500',
    border: 'border-slate-600/50',
    buttonVariant: 'btn-secondary',
    features: [
      { text: '5 video generations / month', included: true },
      { text: '720p export quality', included: true },
      { text: 'Basic templates', included: true },
      { text: 'Community support', included: true },
      { text: 'API access', included: false },
      { text: 'Custom voice cloning', included: false },
      { text: 'Priority queue', included: false },
      { text: 'Team collaboration', included: false },
    ],
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/month',
    description: 'For content creators & small teams',
    icon: Zap,
    color: 'from-indigo-500 to-purple-600',
    border: 'border-indigo-500/50',
    buttonVariant: 'btn-primary',
    popular: true,
    features: [
      { text: 'Unlimited video generations', included: true },
      { text: '4K export quality', included: true },
      { text: 'All templates', included: true },
      { text: 'Priority support', included: true },
      { text: 'API access', included: true },
      { text: 'Custom voice cloning', included: true },
      { text: 'Priority queue', included: true },
      { text: 'Team collaboration', included: false },
    ],
  },
  {
    name: 'Enterprise',
    price: '$99',
    period: '/month',
    description: 'For businesses & power users',
    icon: Shield,
    color: 'from-amber-400 to-orange-500',
    border: 'border-amber-500/40',
    buttonVariant: 'btn-secondary',
    features: [
      { text: 'Unlimited video generations', included: true },
      { text: '4K export quality', included: true },
      { text: 'All templates + custom', included: true },
      { text: 'Dedicated support', included: true },
      { text: 'API access + higher rate limits', included: true },
      { text: 'Custom voice cloning', included: true },
      { text: 'Dedicated GPU queue', included: true },
      { text: 'Team collaboration', included: true },
    ],
  },
]

const allFeatures = [
  'Video generations',
  'Export quality',
  'Templates',
  'Support',
  'API access',
  'Custom voice cloning',
  'Queue priority',
  'Team collaboration',
]

const featureDetails = [
  { free: '5/mo', pro: 'Unlimited', enterprise: 'Unlimited' },
  { free: '720p', pro: '4K', enterprise: '4K' },
  { free: 'Basic', pro: 'All', enterprise: 'All + Custom' },
  { free: 'Community', pro: 'Priority', enterprise: 'Dedicated' },
  { free: '—', pro: '✓', enterprise: 'Higher limits' },
  { free: '—', pro: '✓', enterprise: '✓' },
  { free: '—', pro: 'Priority', enterprise: 'Dedicated GPU' },
  { free: '—', pro: '—', enterprise: '✓' },
]

export default function PlansPage() {
  const [currentPlan] = useState('Free')
  const [subscribing, setSubscribing] = useState<string | null>(null)

  const handleSubscribe = async (planName: string) => {
    if (planName === currentPlan) {
      toast('You are already on this plan', { icon: 'ℹ️' })
      return
    }
    setSubscribing(planName)
    try {
      await subscribe(planName.toLowerCase())
      toast.success(`Subscribed to ${planName} plan!`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Subscription failed')
    } finally {
      setSubscribing(null)
    }
  }

  return (
    <div className="p-6 lg:p-8 space-y-10 animate-fade-in">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-white">Simple, Transparent Pricing</h1>
        <p className="text-slate-400 mt-2">
          Choose the plan that fits your needs. Upgrade or downgrade anytime.
        </p>
      </div>

      {/* Plan Cards */}
      <div className="grid gap-6 lg:grid-cols-3 max-w-5xl mx-auto">
        {plans.map((plan) => {
          const isCurrent = plan.name === currentPlan
          const Icon = plan.icon
          return (
            <div
              key={plan.name}
              className={`relative glass-card p-6 flex flex-col transition-all duration-300 hover:scale-[1.02] ${plan.border} ${
                isCurrent ? 'ring-2 ring-indigo-500' : ''
              }`}
            >
              {/* Popular badge */}
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 text-xs font-semibold text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full shadow-lg">
                    Most Popular
                  </span>
                </div>
              )}

              {/* Current badge */}
              {isCurrent && (
                <div className="absolute top-3 right-3">
                  <span className="px-2 py-0.5 text-[10px] font-semibold text-indigo-300 bg-indigo-500/20 border border-indigo-500/30 rounded-full">
                    CURRENT
                  </span>
                </div>
              )}

              {/* Icon */}
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${plan.color} flex items-center justify-center mb-4`}>
                <Icon className="h-6 w-6 text-white" />
              </div>

              {/* Name & Price */}
              <h3 className="text-lg font-bold text-white">{plan.name}</h3>
              <p className="text-sm text-slate-400 mt-1">{plan.description}</p>
              <div className="mt-4 mb-6">
                <span className="text-4xl font-bold text-white">{plan.price}</span>
                <span className="text-slate-400 text-sm ml-1">{plan.period}</span>
              </div>

              {/* Features */}
              <ul className="space-y-3 flex-1">
                {plan.features.map((feat, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    {feat.included ? (
                      <Check className="h-4 w-4 text-green-400 mt-0.5 flex-shrink-0" />
                    ) : (
                      <X className="h-4 w-4 text-slate-600 mt-0.5 flex-shrink-0" />
                    )}
                    <span className={feat.included ? 'text-slate-300' : 'text-slate-600'}>
                      {feat.text}
                    </span>
                  </li>
                ))}
              </ul>

              {/* Subscribe Button */}
              <button
                onClick={() => handleSubscribe(plan.name)}
                disabled={subscribing !== null}
                className={`mt-6 w-full ${plan.buttonVariant} ${
                  isCurrent ? 'opacity-60 cursor-not-allowed' : ''
                }`}
              >
                {subscribing === plan.name ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Subscribing...
                  </>
                ) : isCurrent ? (
                  'Current Plan'
                ) : (
                  `Subscribe to ${plan.name}`
                )}
              </button>
            </div>
          )
        })}
      </div>

      {/* Feature Comparison Table */}
      <div className="glass-card p-6 max-w-5xl mx-auto">
        <h2 className="text-lg font-semibold text-white mb-6">Full Feature Comparison</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-3 px-4 text-slate-400 font-medium">Feature</th>
                <th className="text-center py-3 px-4 text-slate-300 font-medium">Free</th>
                <th className="text-center py-3 px-4 text-indigo-400 font-medium">Pro</th>
                <th className="text-center py-3 px-4 text-amber-400 font-medium">Enterprise</th>
              </tr>
            </thead>
            <tbody>
              {allFeatures.map((feature, i) => (
                <tr key={feature} className="border-b border-slate-800 last:border-0">
                  <td className="py-3 px-4 text-slate-300">{feature}</td>
                  <td className="py-3 px-4 text-center text-slate-500">{featureDetails[i].free}</td>
                  <td className="py-3 px-4 text-center text-indigo-300">{featureDetails[i].pro}</td>
                  <td className="py-3 px-4 text-center text-amber-300">{featureDetails[i].enterprise}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
