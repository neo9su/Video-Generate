'use client'

import { usePathname } from 'next/navigation'
import { Toaster } from 'react-hot-toast'
import Sidebar from '@/components/Layout/Sidebar'
import Header from '@/components/Layout/Header'

const publicPaths = ['/']

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isPublic = publicPaths.includes(pathname)

  if (isPublic) {
    return (
      <>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1e293b',
              color: '#e2e8f0',
              border: '1px solid #334155',
              borderRadius: '12px',
            },
            success: {
              iconTheme: { primary: '#22c55e', secondary: '#1e293b' },
            },
            error: {
              iconTheme: { primary: '#ef4444', secondary: '#1e293b' },
            },
          }}
        />
      </>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto bg-slate-900">
          {children}
        </main>
      </div>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#e2e8f0',
            border: '1px solid #334155',
            borderRadius: '12px',
          },
          success: {
            iconTheme: { primary: '#22c55e', secondary: '#1e293b' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#1e293b' },
          },
        }}
      />
    </div>
  )
}
