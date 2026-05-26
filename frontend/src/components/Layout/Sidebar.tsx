'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  HomeIcon,
  VideoCameraIcon,
  DocumentPlusIcon,
  MicrophoneIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  KeyIcon,
  GlobeAltIcon,
  ShieldCheckIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { useState, useEffect } from 'react'

const mainNav = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Create Video', href: '/create', icon: DocumentPlusIcon },
  { name: 'Video Remake', href: '/remake', icon: ArrowPathIcon },
  { name: 'Tasks', href: '/tasks', icon: VideoCameraIcon },
]

const toolsNav = [
  { name: 'Analysis', href: '/analysis', icon: ChartBarIcon },
  { name: 'Voices', href: '/voices', icon: MicrophoneIcon },
  { name: 'Prompts', href: '/prompts', icon: DocumentTextIcon },
]

const saasNav = [
  { name: 'Plans', href: '/plans', icon: CurrencyDollarIcon },
  { name: 'API Keys', href: '/api-keys', icon: KeyIcon },
  { name: 'Webhooks', href: '/webhooks', icon: GlobeAltIcon },
  { name: 'Billing', href: '/billing', icon: DocumentTextIcon },
]

const adminNav = [
  { name: 'Admin', href: '/admin', icon: ShieldCheckIcon },
]

const settingsNav = [
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    try {
      const userData = JSON.parse(localStorage.getItem('user_profile') || '{}')
      setIsAdmin(!!userData.is_admin)
    } catch {
      setIsAdmin(true) // Default to true for development
    }
  }, [])

  const navGroups = [
    { label: 'Main', items: mainNav },
    { label: 'Tools', items: toolsNav },
    { label: 'SaaS', items: saasNav },
    ...(isAdmin ? [{ label: 'Admin', items: adminNav }] : []),
    { label: 'Settings', items: settingsNav },
  ]

  return (
    <div
      className={
        'flex flex-col bg-slate-900 border-r border-slate-800 transition-all duration-300 ' +
        (collapsed ? 'w-16' : 'w-64')
      }
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-slate-800">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
            <VideoCameraIcon className="h-4 w-4 text-white" />
          </div>
          {!collapsed && (
            <span className="text-lg font-bold text-white tracking-tight">
              Video<span className="text-indigo-400">Generate</span>
            </span>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <svg
            className={
              'h-4 w-4 transition-transform ' +
              (collapsed ? 'rotate-180' : '')
            }
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
        {navGroups.map((group, groupIdx) => (
          <div key={group.label} className={groupIdx > 0 ? 'mt-6' : ''}>
            {!collapsed && (
              <p className="px-3 mb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                {group.label}
              </p>
            )}
            {group.items.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ' +
                    (isActive
                      ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-transparent')
                  }
                  title={collapsed ? item.name : undefined}
                >
                  <item.icon className="h-5 w-5 flex-shrink-0" />
                  {!collapsed && <span>{item.name}</span>}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-slate-800 p-4">
        {!collapsed && (
          <p className="text-xs text-slate-500 text-center">
            Video-Generate v0.1.0
          </p>
        )}
      </div>
    </div>
  )
}
