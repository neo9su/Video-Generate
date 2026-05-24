'use client'

import Link from 'next/link'
import { Sparkles, Video, Globe, Palette, Zap, Shield } from 'lucide-react'

const features = [
  {
    icon: Video,
    title: 'AI-Powered Generation',
    description: 'Transform product descriptions into stunning videos with state-of-the-art AI models.',
  },
  {
    icon: Globe,
    title: 'Multi-Platform Support',
    description: 'Optimized for TikTok, Instagram, Amazon, Shopify, and more.',
  },
  {
    icon: Palette,
    title: 'Customizable Styles',
    description: 'Choose from Apple, Tech, Premium, Trendy, Minimal and more visual styles.',
  },
  {
    icon: Zap,
    title: 'Fast Processing',
    description: 'Generate high-quality videos in minutes, not hours.',
  },
  {
    icon: Shield,
    title: 'Enterprise Grade',
    description: 'Secure, scalable, and production-ready for your business needs.',
  },
  {
    icon: Sparkles,
    title: 'Voice Integration',
    description: 'Add natural voiceovers with text-to-speech and voice cloning.',
  },
]

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-900">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-slate-800 bg-slate-900/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
                <Video className="h-4 w-4 text-white" />
              </div>
              <span className="text-lg font-bold text-white tracking-tight">
                Video<span className="text-indigo-400">Generate</span>
              </span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/dashboard"
                className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
              >
                Dashboard
              </Link>
              <Link
                href="/create"
                className="btn-primary"
              >
                <Sparkles className="h-4 w-4" />
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-32 pb-20">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/5 via-transparent to-transparent" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-r from-indigo-500/10 to-purple-500/10 rounded-full blur-3xl" />

        <div className="relative mx-auto max-w-7xl px-6 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-4 py-1.5 text-sm text-indigo-400 mb-8">
            <Sparkles className="h-4 w-4" />
            <span>AI-Powered Video Generation Platform</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white mb-6">
            Create Product Videos
            <br />
            <span className="gradient-text">with AI in Minutes</span>
          </h1>

          <p className="mx-auto max-w-2xl text-lg text-slate-400 mb-10">
            Upload your product images and descriptions, and let our AI generate
            stunning promotional videos optimized for any platform. No video editing
            skills required.
          </p>

          <div className="flex items-center justify-center gap-4">
            <Link
              href="/create"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-500/25 hover:bg-indigo-500 transition-all duration-200"
            >
              <Sparkles className="h-5 w-5" />
              Create Your First Video
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-8 py-4 text-base font-semibold text-slate-200 hover:bg-slate-700 transition-all duration-200"
            >
              View Dashboard
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 border-t border-slate-800">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">
              Everything you need to create
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Powerful features designed for e-commerce businesses of all sizes
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon
              return (
                <div
                  key={feature.title}
                  className="glass-card p-6 hover:border-slate-600/50 transition-all duration-200 group"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/10 group-hover:bg-indigo-500/20 transition-colors">
                    <Icon className="h-6 w-6 text-indigo-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-sm text-slate-400">{feature.description}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 border-t border-slate-800 bg-slate-900/50">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">
              How it works
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Three simple steps to create professional product videos
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {[
              {
                step: '01',
                title: 'Upload Images',
                description: 'Upload your product images or screenshots. We support PNG, JPG, and WebP formats.',
              },
              {
                step: '02',
                title: 'Describe & Configure',
                description: 'Write a product description and choose platform, style, and voice settings.',
              },
              {
                step: '03',
                title: 'Generate & Download',
                description: 'Our AI generates your video. Preview, refine, and download in minutes.',
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 mb-6">
                  <span className="text-xl font-bold text-indigo-400">{item.step}</span>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-sm text-slate-400 px-4">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 border-t border-slate-800">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to create your first video?
          </h2>
          <p className="text-slate-400 mb-8 max-w-lg mx-auto">
            Join thousands of businesses using Video-Generate to create compelling product content.
          </p>
          <Link
            href="/create"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-500/25 hover:bg-indigo-500 transition-all duration-200"
          >
            <Sparkles className="h-5 w-5" />
            Get Started Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-6 w-6 items-center justify-center rounded bg-gradient-to-br from-indigo-500 to-purple-600">
                <Video className="h-3 w-3 text-white" />
              </div>
              <span className="text-sm text-slate-400">
                Video-Generate &copy; {new Date().getFullYear()}
              </span>
            </div>
            <div className="flex items-center gap-6">
              <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                Dashboard
              </Link>
              <Link href="/create" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                Create
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </main>
  )
}
