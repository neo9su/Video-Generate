'use client'

import { useState, useRef, useEffect } from 'react'
import { Bell, User, Settings, LogOut, ChevronDown } from 'lucide-react'

export default function Header() {
  const [showNotifications, setShowNotifications] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const notifRef = useRef<HTMLDivElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const [notifications] = useState([
    { id: 1, text: 'Task "Product Demo" completed', time: '2 min ago' },
    { id: 2, text: 'New voice clone ready', time: '1 hour ago' },
  ])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900/80 backdrop-blur-xl px-6">
      <div />

      <div className="flex items-center gap-3">
        {/* Notifications */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative rounded-lg p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <Bell className="h-5 w-5" />
            {notifications.length > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-bold text-white">
                {notifications.length}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 origin-top-right rounded-xl border border-slate-700 bg-slate-800 shadow-2xl ring-1 ring-black ring-opacity-5 animate-fade-in">
              <div className="px-4 py-3 border-b border-slate-700">
                <p className="text-sm font-semibold text-white">Notifications</p>
              </div>
              <div className="max-h-60 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="px-4 py-6 text-center text-sm text-slate-400">
                    No notifications yet
                  </p>
                ) : (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      className="px-4 py-3 hover:bg-slate-700/50 cursor-pointer transition-colors"
                    >
                      <p className="text-sm text-slate-200">{notif.text}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{notif.time}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Menu */}
        <div ref={userMenuRef} className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-xs font-bold text-white">
              U
            </div>
            <span className="hidden sm:block text-sm font-medium text-slate-200">User</span>
            <ChevronDown className="h-4 w-4 text-slate-500" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 origin-top-right rounded-xl border border-slate-700 bg-slate-800 shadow-2xl ring-1 ring-black ring-opacity-5 animate-fade-in">
              <div className="px-4 py-3 border-b border-slate-700">
                <p className="text-sm font-medium text-white">User</p>
                <p className="text-xs text-slate-400 mt-0.5">user@example.com</p>
              </div>
              <div className="py-1">
                <button className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700/50">
                  <User className="h-4 w-4" />
                  Profile
                </button>
                <button className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700/50">
                  <Settings className="h-4 w-4" />
                  Settings
                </button>
              </div>
              <div className="border-t border-slate-700 py-1">
                <button className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-slate-700/50">
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
